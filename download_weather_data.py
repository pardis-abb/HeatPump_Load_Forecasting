from pathlib import Path
import requests

print("Script started")

CLIMATE_ID = "3031092"

OUTPUT_FOLDER = Path("datasets/weather_data")
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

months_to_download = [
    (2023, 11), (2023, 12),
    (2024, 1), (2024, 2), (2024, 3), (2024, 4),
    (2024, 5), (2024, 6), (2024, 7), (2024, 8),
    (2024, 9), (2024, 10), (2024, 11), (2024, 12),
]

for year, month in months_to_download:
    filename = f"en_climate_hourly_AB_{CLIMATE_ID}_{month:02d}-{year}_P1H.csv"
    filepath = OUTPUT_FOLDER / filename

    if filepath.exists():
        print(f"Already exists, skipping: {filename}")
        continue

    url = (
        "https://climate.weather.gc.ca/climate_data/bulk_data_e.html"
        f"?format=csv"
        f"&timeframe=1"
        f"&Year={year}"
        f"&Month={month}"
        f"&Day=1"
        f"&climate_id={CLIMATE_ID}"
    )

    print(f"Downloading {filename}...")

    response = requests.get(url)

    if response.status_code == 200 and "Temp" in response.text:
        filepath.write_text(response.text, encoding="utf-8-sig")
        print(f"Saved: {filepath}")
    else:
        print(f"Failed: {filename}")
        print(response.text[:300])

print("Done downloading weather data.")