"""
oi_buildup.py
---------------------------------
Downloader for Nifty Spot + Options intraday OHLC data (via Breeze API).
- Spot data at 5min interval
- Options data at 30min interval
- Saves data into data/fno/ consistently
- Automatically runs intraday OI analysis after download
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta

from scripts.breeze_client import get_breeze
from scripts.oi_analysis_intraday import analyze_intraday   # 👈 intraday analysis


# ============== DIRECTORIES ==============
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FNO_DIR = os.path.join(PROJECT_ROOT, "data", "fno")
os.makedirs(FNO_DIR, exist_ok=True)

# ============== HOLIDAY + TRADING DAY HELPER ==============
HOLIDAYS = {
    "2025-01-26", "2025-03-14", "2025-04-10", "2025-04-14", "2025-04-18",
    "2025-05-01", "2025-08-15", "2025-08-27", "2025-10-02", "2025-10-21",
    "2025-10-22", "2025-11-05", "2025-12-25"
}

def get_last_trading_day(date_str: str) -> str:
    """Roll back to last working day if input is weekend/holiday."""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    while date.strftime("%Y-%m-%d") in HOLIDAYS or date.weekday() >= 5:
        date -= timedelta(days=1)
    return date.strftime("%Y-%m-%d")


# ============== INITIALIZE BREEZE CLIENT ==============
breeze = get_breeze()


# ============== SPOT DATA ==============
def download_spot_data(date: str):
    """Download Nifty spot OHLC at 5min interval and save to CSV."""
    try:
        data = breeze.get_historical_data(
            interval="5minute",
            from_date=f"{date}T07:00:00.000Z",
            to_date=f"{date}T18:00:00.000Z",
            stock_code="NIFTY",
            exchange_code="NSE",
            product_type="cash"
        )
        if "Success" in data and data["Success"]:
            df = pd.DataFrame(data["Success"])
            file_path = os.path.join(FNO_DIR, f"Nifty_{date}.csv")
            df.to_csv(file_path, index=False)
            print(f"✅ Spot saved: {file_path} ({len(df)} rows)")
            return file_path
        else:
            print(f"⚠️ No spot data for {date}")
    except Exception as e:
        print(f"❌ Spot download failed for {date}: {e}")
    return None


# ============== OPTIONS DATA ==============
def download_options_data(date: str, expiry: str, atm_strike: int,
                          strikes: int = 10, step: int = 100):
    """Download options OHLC at 30min interval across a strike range."""
    min_strike = atm_strike - (strikes * step)
    max_strike = atm_strike + (strikes * step)
    option_types = ["call", "put"]

    data_collection = []

    for strike in range(min_strike, max_strike + 1, step):
        for option_type in option_types:
            try:
                data = breeze.get_historical_data(
                    interval="30minute",
                    from_date=f"{date}T07:00:00.000Z",
                    to_date=f"{date}T18:00:00.000Z",
                    stock_code="NIFTY",
                    exchange_code="NFO",
                    product_type="options",
                    expiry_date=f"{expiry}T07:00:00.000Z",
                    right=option_type,
                    strike_price=strike
                )
                if "Success" in data and data["Success"]:
                    df = pd.DataFrame(data["Success"])
                    df["Strike"] = strike
                    df["Option Type"] = option_type.capitalize()
                    data_collection.append(df)
                else:
                    print(f"⚠️ No {option_type} {strike} data for {date}")
            except Exception as e:
                print(f"❌ Failed {option_type} {strike} on {date}: {e}")
            time.sleep(1)  # rate-limit

    if data_collection:
        final_df = pd.concat(data_collection, ignore_index=True)
        file_path = os.path.join(FNO_DIR, f"Nifty_Options_{date}.csv")
        final_df.to_csv(file_path, index=False)
        print(f"✅ Options saved: {file_path} ({len(final_df)} rows)")
        return file_path
    else:
        print(f"⚠️ No options data for {date}")
        return None


# ============== MAIN RUNNER ==============
def download_snapshot(date_of_snapshot: str, expiry: str):
    """Download spot (5min) + options (30min) for snapshot and prev day,
    then run intraday OI analysis automatically.
    """
    # Resolve dates
    snapshot = get_last_trading_day(date_of_snapshot)
    prev_day = get_last_trading_day(
        (datetime.strptime(snapshot, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    )

    # Spot price → ATM strike with fallback
    try:
        quote = breeze.get_quotes(
            stock_code="NIFTY",
            exchange_code="NSE",
            product_type="cash",
            right="others"
        )
        if not quote.get("Success"):
            raise ValueError(f"No LTP found, response: {quote}")
        nifty_spot = float(quote["Success"][0].get("ltp", 0))
        print(f"✅ Nifty Spot fetched from Breeze: {nifty_spot}")
    except Exception as e:
        print(f"⚠️ Could not fetch Nifty Spot via Breeze: {e}")
        nifty_spot = float(input("Please enter the current Nifty Spot manually: "))
        print(f"✔️ Using manual Nifty Spot: {nifty_spot}")

    atm_strike = round(nifty_spot / 100) * 100
    print(f"📌 ATM Strike set to: {atm_strike}")

    # --- Download data ---
    download_spot_data(snapshot)
    download_spot_data(prev_day)
    download_options_data(snapshot, expiry, atm_strike)
    download_options_data(prev_day, expiry, atm_strike)

    print(f"📊 Download complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # --- Run intraday analysis ---
    try:
        intraday, three_hr, summary = analyze_intraday(snapshot)

        print("\n=== Intraday Trends ===")
        print(intraday.to_string(index=False))

        print("\n=== 3-Hour Interval Trends ===")
        print(three_hr.to_string(index=False))

        print("\n=== Session Summary ===")
        for k, v in summary.items():
            print(f"{k}: {v}")
    except Exception as e:
        print(f"⚠️ Analysis failed: {e}")
