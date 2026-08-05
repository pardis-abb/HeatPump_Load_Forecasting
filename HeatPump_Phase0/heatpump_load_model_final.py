"""
Calgary Heat Pump Hourly Electrical Load Model
================================================
FINAL v2 — for local use (VS Code / plain Python), consolidating everything
built and debugged in this conversation.

USAGE
-----
    python3 heatpump_load_model.py --date 2026-01-15
    python3 heatpump_load_model.py --date 2006-02-18
    python3 heatpump_load_model.py --date 2030-01-01

SETUP
-----
1. pip install pandas numpy matplotlib requests
2. Put these 4 files in a folder called "data" next to this script
   (or point --data-dir at wherever they are):
     - weatherstats_calgary_hourly.csv
     - weatherstats_calgary_forecast_hourly.csv
     - weatherstats_calgary_normal_daily.csv
     - weatherstats_calgary_normal_monthly.csv  (not currently used, kept for future use)

WHAT THIS DOES
--------------
Picks an outdoor temperature source for the requested date, in this order:
  1. Actual recent station data       -> weatherstats_calgary_hourly.csv
  2. Hourly forecast data              -> weatherstats_calgary_forecast_hourly.csv
  3. Real historical archive           -> live pull from Environment and
                                           Climate Change Canada (ECCC),
                                           Calgary Int'l Airport station,
                                           covering ~1953-present
  4. 30-yr climate normals             -> weatherstats_calgary_normal_daily.csv
                                           (synthesized diurnal curve; used
                                           only outside all of the above,
                                           e.g. before 1953 or far future)

Then splits the regional heat pump stock into 4 technology types, computes
hourly building heat demand, applies temperature-dependent COP per type,
and sums to a total hourly electrical load (MW) for Calgary.

EVERY NUMBER THAT ISN'T FROM REAL DATA IS A STATED ASSUMPTION — see the
ASSUMPTIONS block below, sourced primarily from getenergy.ca's "Heat Pumps
in Alberta" guide and NRCan's Greener Homes Feb-2025 progress update.
"""

import argparse
import io
import math
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt

# ============================================================================
# PATHS
# ============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = SCRIPT_DIR / "data"
DEFAULT_OUT_DIR = SCRIPT_DIR / "outputs"

# ============================================================================
# ASSUMPTIONS
# ============================================================================

# --- 1. Regional heat pump stock -------------------------------------------
# Source: NRCan "Greener Homes Initiative progress update: February 2025"
# -> Alberta = 2,192 heat pumps installed with federal support.
# (NOTE: an earlier draft of this figure, 57,826, is actually Quebec's
# number, not Alberta's -- corrected here.)
ALBERTA_HEATPUMPS_FEB2025 = 2192
CALGARY_POP_SHARE_OF_ALBERTA = 0.35  # as specified by user
DEFAULT_CALGARY_HP_STOCK = round(ALBERTA_HEATPUMPS_FEB2025 * CALGARY_POP_SHARE_OF_ALBERTA)
# This only captures federally-rebated installs, so it's a lower bound on
# true stock. Exposed as --stock so a better estimate can be substituted,
# but no longer required input -- it defaults automatically.

# --- 2. Technology mix (source: getenergy.ca "Heat Pumps in Alberta" guide) -
# No public Alberta-specific type breakdown exists; shares below are an
# assumption informed by the article's framing of what's common/practical
# in Alberta.
TYPE_SHARES = {
    "ducted_ashp":        0.40,  # whole-home ducted air-source heat pump
    "ductless_minisplit": 0.25,  # partial-home / zonal ductless mini-split
    "hybrid_dualfuel":    0.30,  # ASHP + gas furnace backup
    "ground_source":      0.05,  # geothermal
}
assert abs(sum(TYPE_SHARES.values()) - 1.0) < 1e-9

# --- 3. Rated heating capacity per unit (source: getenergy.ca sizing table) -
TON_TO_KW = 3.517
CAPACITY_KW = {
    "ducted_ashp":        3.5 * TON_TO_KW,
    "ductless_minisplit": 1.5 * TON_TO_KW,
    "hybrid_dualfuel":    3.5 * TON_TO_KW,
    "ground_source":      4.0 * TON_TO_KW,
}

# --- 4. COP vs outdoor temperature (source: getenergy.ca performance bins) --
def cop_air_source(temp_c: float) -> float:
    if temp_c >= -10:
        return 3.5
    elif temp_c >= -20:
        return 3.5 + (2.0 - 3.5) * (-10 - temp_c) / 10
    else:
        cop = 2.0 + (1.2 - 2.0) * (-20 - temp_c) / 10
        return max(cop, 1.2)

GROUND_SOURCE_COP = 4.2  # ~constant, ground loop stays ~8-10C year-round

# --- 5. Hybrid dual-fuel switchover -----------------------------------------
HYBRID_SWITCHOVER_C = -17.5  # midpoint of getenergy.ca's -15C to -20C range

# --- 6. Building heat demand model ------------------------------------------
T_BALANCE_C = 18.0
CALGARY_DESIGN_TEMP_C = -30.0  # Calgary ~99% winter design temp (NBC reference)

def ua_for(capacity_kw: float) -> float:
    return capacity_kw / (T_BALANCE_C - CALGARY_DESIGN_TEMP_C)

UA = {t: ua_for(c) for t, c in CAPACITY_KW.items()}

# ============================================================================
# REAL HISTORICAL DATA (ECCC archive) — covers ~1953-present
# ============================================================================

STATION_INVENTORY_URL = (
    "https://collaboration.cmc.ec.gc.ca/cmc/climate/"
    "Get_More_Data_Plus_de_donnees/Station%20Inventory%20EN.csv"
)

_station_inventory_cache = None

def _load_station_inventory():
    global _station_inventory_cache
    if _station_inventory_cache is None:
        resp = requests.get(STATION_INVENTORY_URL, timeout=30)
        resp.raise_for_status()
        _station_inventory_cache = pd.read_csv(io.StringIO(resp.text), skiprows=3)
    return _station_inventory_cache


def _find_calgary_station_id(year: int):
    """
    Finds the correct Calgary Int'l Airport station ID for a given year.
    ECCC has used two station IDs for this location over time:
      - Station 2205  "CALGARY INT'L A"  -> hourly data 1953-2012
      - Station 50430 "CALGARY INTL A"   -> hourly data 2012-present
    """
    inv = _load_station_inventory()
    candidates = inv[inv["Name"].str.contains(r"CALGARY INT'?L A", na=False, regex=True, case=False)]
    candidates = candidates.dropna(subset=["HLY First Year", "HLY Last Year"])
    match = candidates[
        (candidates["HLY First Year"] <= year) & (candidates["HLY Last Year"] >= year)
    ]
    if match.empty:
        return None
    return int(match.iloc[0]["Station ID"])


def load_real_historical_hourly_temps(target_date: pd.Timestamp):
    """
    Downloads REAL observed hourly temperatures for target_date from ECCC's
    bulk data endpoint. Returns None if no station covers that year (e.g.
    dates before ~1953, or future dates) or the day's record is incomplete.
    """
    station_id = _find_calgary_station_id(target_date.year)
    if station_id is None:
        return None

    url = (
        "https://climate.weather.gc.ca/climate_data/bulk_data_e.html"
        f"?format=csv&stationID={station_id}"
        f"&Year={target_date.year}&Month={target_date.month}&Day={target_date.day}"
        "&timeframe=1&submit=Download+Data"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    raw = pd.read_csv(io.StringIO(resp.text))

    raw["dt"] = pd.to_datetime(raw["Date/Time (LST)"])
    day_rows = raw[raw["dt"].dt.date == target_date.date()]
    if len(day_rows) < 20:
        return None

    temps = {row["dt"].hour: row["Temp (\u00b0C)"] for _, row in day_rows.iterrows()}
    return temps

# ============================================================================
# TEMPERATURE SOURCE SELECTION
# ============================================================================

def synthesize_diurnal_curve(tmin, tmax, trough_hour=6, peak_hour=15):
    """
    Builds a 24-hour temperature curve from a daily min/max using an
    asymmetric double-cosine shape (fast rise to peak, slower overnight
    fall). Used only when no actual/forecast/real-historical hourly data
    exists for the date.
    """
    rise_len = (peak_hour - trough_hour) % 24
    fall_len = 24 - rise_len
    temps = {}
    for h in range(24):
        if trough_hour <= h < peak_hour:
            frac = (h - trough_hour) / rise_len
            temps[h] = tmin + (tmax - tmin) * (1 - math.cos(math.pi * frac)) / 2
        else:
            h_adj = h if h >= peak_hour else h + 24
            frac = (h_adj - peak_hour) / fall_len
            temps[h] = tmax - (tmax - tmin) * (1 - math.cos(math.pi * frac)) / 2
    return temps


def load_hourly_temps(target_date: pd.Timestamp, data_dir: Path):
    day_start = target_date.normalize()
    day_end = day_start + timedelta(days=1)

    # 1. actual recent station data
    hist = pd.read_csv(data_dir / "weatherstats_calgary_hourly.csv")
    hist["dt"] = pd.to_datetime(hist["date_time_local"].str.replace(r" [A-Z]{3,4}$", "", regex=True))
    day_hist = hist[(hist["dt"] >= day_start) & (hist["dt"] < day_end)]
    if len(day_hist) >= 20:
        temps = {row.dt.hour: row.temperature for row in day_hist.itertuples()}
        return temps, "actual historical station data (recent)"

    # 2. forecast data
    fc = pd.read_csv(data_dir / "weatherstats_calgary_forecast_hourly.csv")
    fc["dt"] = pd.to_datetime(fc["period_string"])
    day_fc = fc[(fc["dt"] >= day_start) & (fc["dt"] < day_end)]
    if len(day_fc) >= 20:
        temps = {row.dt.hour: row.temperature for row in day_fc.itertuples()}
        return temps, "hourly forecast data"

    # 3. real ECCC historical archive (~1953-present)
    real_hist = load_real_historical_hourly_temps(target_date)
    if real_hist is not None:
        return real_hist, "real ECCC historical station data (archive)"

    # 4. fallback: synthesized from 30-yr climate normals
    nd = pd.read_csv(data_dir / "weatherstats_calgary_normal_daily.csv")
    nd["date"] = pd.to_datetime(nd["date"])
    same_md = nd[(nd["date"].dt.month == target_date.month) & (nd["date"].dt.day == target_date.day)]
    if len(same_md) == 0:
        raise ValueError(f"No climate normal found for {target_date.date()}")
    tmax = same_md["max_temperature_v"].mean()
    tmin = same_md["min_temperature_v"].mean()
    temps = synthesize_diurnal_curve(tmin, tmax)
    return temps, f"synthesized from 30-yr climate normals (mean high {tmax:.1f}C / low {tmin:.1f}C)"

# ============================================================================
# LOAD CALCULATION
# ============================================================================

def compute_hourly_load(target_date: pd.Timestamp, total_stock: int, data_dir: Path):
    temps, source_label = load_hourly_temps(target_date, data_dir)
    hours = sorted(temps.keys())

    rows = []
    for h in hours:
        T = temps[h]
        total_kw = 0.0
        breakdown = {}
        for hp_type, share in TYPE_SHARES.items():
            count = total_stock * share
            capacity = CAPACITY_KW[hp_type]
            demand_kw = UA[hp_type] * max(0.0, T_BALANCE_C - T)

            if hp_type == "hybrid_dualfuel" and T < HYBRID_SWITCHOVER_C:
                hp_output_kw = 0.0
            else:
                hp_output_kw = min(demand_kw, capacity)

            cop = GROUND_SOURCE_COP if hp_type == "ground_source" else cop_air_source(T)
            elec_kw_per_unit = hp_output_kw / cop if hp_output_kw > 0 else 0.0
            type_total_kw = elec_kw_per_unit * count
            breakdown[hp_type] = type_total_kw
            total_kw += type_total_kw

        row = {"hour": h, "temperature_c": T, "total_load_mw": total_kw / 1000.0}
        for hp_type in TYPE_SHARES:
            row[f"{hp_type}_mw"] = breakdown[hp_type] / 1000.0
        rows.append(row)

    df = pd.DataFrame(rows).sort_values("hour").reset_index(drop=True)
    return df, source_label

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Calgary residential heat pump hourly load model")
    parser.add_argument("--date", required=True, help="Target date, YYYY-MM-DD")
    parser.add_argument("--stock", type=int, default=DEFAULT_CALGARY_HP_STOCK,
                         help=f"Total Calgary heat pump count (default {DEFAULT_CALGARY_HP_STOCK}, "
                              f"auto-derived from Alberta's {ALBERTA_HEATPUMPS_FEB2025} Feb-2025 "
                              f"figure x {CALGARY_POP_SHARE_OF_ALBERTA} population share)")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                         help=f"Folder containing the weatherstats CSVs (default: {DEFAULT_DATA_DIR})")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                         help=f"Folder to save results (default: {DEFAULT_OUT_DIR})")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    target_date = pd.Timestamp(args.date)
    df, source_label = compute_hourly_load(target_date, args.stock, args.data_dir)

    print("=" * 70)
    print(f"Calgary Heat Pump Hourly Load Estimate — {target_date.date()}")
    print("=" * 70)
    print(f"Temperature source: {source_label}")
    print(f"Assumed total Calgary heat pump stock: {args.stock:,}")
    print("Type mix: " + ", ".join(f"{k} {v:.0%}" for k, v in TYPE_SHARES.items()))
    print(f"Peak hourly load: {df['total_load_mw'].max():.2f} MW "
          f"at hour {int(df.loc[df['total_load_mw'].idxmax(), 'hour']):02d}:00")
    print(f"Daily energy: {df['total_load_mw'].sum():.1f} MWh")
    print("=" * 70)

    csv_path = args.out_dir / f"calgary_hp_load_{target_date.date()}.csv"
    df.to_csv(csv_path, index=False)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    ax1.plot(df["hour"], df["total_load_mw"], color="#c0392b", linewidth=2.5, marker="o")
    ax1.set_ylabel("Heat pump load (MW)")
    ax1.set_title(f"Calgary Residential Heat Pump Load — {target_date.date()}\n"
                   f"(stock={args.stock:,}, temp source: {source_label})", fontsize=11)
    ax1.grid(alpha=0.3)
    for hp_type in TYPE_SHARES:
        ax1.fill_between(df["hour"], 0, df[f"{hp_type}_mw"], alpha=0.15)

    ax2.plot(df["hour"], df["temperature_c"], color="#2980b9", linewidth=2, marker="o")
    ax2.set_xlabel("Hour of day (local)")
    ax2.set_ylabel("Outdoor temp (\u00b0C)")
    ax2.grid(alpha=0.3)
    ax2.set_xticks(range(0, 24, 2))

    plt.tight_layout()
    png_path = args.out_dir / f"calgary_hp_load_{target_date.date()}.png"
    plt.savefig(png_path, dpi=150)
    plt.close()

    print(f"Saved: {csv_path}")
    print(f"Saved: {png_path}")
    return df


if __name__ == "__main__":
    main()
