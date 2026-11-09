
import csv, os, time
import requests

# Open-Meteo Air Quality API
LAT, LON = 45.7640, 4.8357  # Lyon, France  
PAST_DAYS = 90
URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

def fetch_hourly_co2(retries=4, backoff=5):
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": "carbon_dioxide",
        "past_days": PAST_DAYS,
        "forecast_days": 0,
        "timezone": "auto",
    }

    last_error = None

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(
                URL,
                params=params,
                timeout=(15, 30)
            )
            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.RequestException as e:
            last_error = e
            print(
                f"Fetch attempt {attempt}/{retries} failed: {e}"
            )
            if attempt < retries:
                time.sleep(backoff * attempt)

    raise RuntimeError(
        f"Open-Meteo unreachable after {retries} attempts"
    ) from last_error

def aggregate_to_daily(times, values):
    by_day = {}

    for t, v in zip(times, values):
        day = t[:10]
        by_day.setdefault(day, []).append(v)

    rows = []

    for day in sorted(by_day):
        hours = by_day[day]
        real_hours = [h for h in hours if h is not None]

        rows.append({
            "date": day,
            "co2_ppm": round(
                sum(real_hours) / len(real_hours), 1
            ) if real_hours else "",
            "n_hours_observed": len(real_hours),
        })

    return rows

def main():
    print(
        f"Fetching {PAST_DAYS} days of CO2 data for Le Mans..."
    )

    data = fetch_hourly_co2()

    times = data["hourly"]["time"]
    values = data["hourly"]["carbon_dioxide"]

    print(f"Received {len(times)} hourly readings")

    rows = aggregate_to_daily(times, values)

    incomplete = [
        r for r in rows
        if r["n_hours_observed"] < 24
    ]

    print(
        f"Aggregated to {len(rows)} daily values"
    )

    print(
        f"Incomplete days: {len(incomplete)}"
    )

    for r in incomplete:
        print(
            f"Incomplete day: {r['date']} "
            f"({r['n_hours_observed']}/24 hours)"
        )

    os.makedirs("data", exist_ok=True)

    with open(
        "data/series.csv",
        "w",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "date",
                "co2_ppm",
                "n_hours_observed"
            ]
        )

        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Wrote data/series.csv ({len(rows)} days)"
    )

if __name__ == "__main__":
    main()
