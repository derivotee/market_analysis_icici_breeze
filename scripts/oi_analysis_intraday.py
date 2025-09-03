"""
oi_analysis_intraday.py
---------------------------------
Analyze intraday OI buildup trends using spot + options OHLC data
downloaded via Breeze API (from oi_buildup.py).
"""

import os
import pandas as pd
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FNO_DIR = os.path.join(PROJECT_ROOT, "data", "fno")


# ----------------------------
# Load Data
# ----------------------------
def load_csv(file_path):
    """Load CSV and normalize column names."""
    df = pd.read_csv(file_path, parse_dates=["datetime"])
    df.columns = df.columns.str.strip().str.lower()
    if "open_interest" in df.columns:
        df["open_interest"] = pd.to_numeric(df["open_interest"], errors="coerce")
    return df if not df.empty else None


# ----------------------------
# Trend Classifier
# ----------------------------
def classify_trend(oi_change, price_change):
    if pd.isna(oi_change) or pd.isna(price_change):
        return None
    if oi_change > 0 and price_change > 0:
        return "Long Buildup"
    elif oi_change < 0 and price_change > 0:
        return "Short Covering"
    elif oi_change > 0 and price_change < 0:
        return "Short Buildup"
    elif oi_change < 0 and price_change < 0:
        return "Long Unwinding"
    return "Neutral"


# ----------------------------
# Merge & Analyze
# ----------------------------
def analyze_intraday(snapshot_date: str):
    """Analyze intraday OI vs Price for a given date (requires Nifty + Options CSVs)."""

    nifty_file = os.path.join(FNO_DIR, f"Nifty_{snapshot_date}.csv")
    options_file = os.path.join(FNO_DIR, f"Nifty_Options_{snapshot_date}.csv")

    nifty_df = load_csv(nifty_file)
    options_df = load_csv(options_file)

    if nifty_df is None or options_df is None:
        raise ValueError(f"Missing data for {snapshot_date}")

    # --- aggregate options OI by timestamp ---
    oi_by_time = options_df.groupby("datetime")["open_interest"].sum().reset_index()

    # --- align with nifty close prices ---
    merged = oi_by_time.merge(nifty_df[["datetime", "close"]], on="datetime", how="left")
    merged = merged.sort_values("datetime").reset_index(drop=True)

    # --- calculate changes ---
    merged["oi_change"] = merged["open_interest"].diff()
    merged["price_change"] = merged["close"].diff()
    merged["trend"] = merged.apply(
        lambda row: classify_trend(row["oi_change"], row["price_change"]), axis=1
    )

    # --- 3-hour windows (6 x 30min intervals) ---
    merged["3hr_window"] = (merged.index // 6) * 6
    three_hr_trends = (
        merged.groupby("3hr_window")
        .agg({
            "datetime": "last",       # end of the 3h block
            "oi_change": "sum",       # net OI change in block
            "price_change": "sum",    # net price change in block
        })
        .reset_index(drop=True)
    )
    three_hr_trends["trend"] = three_hr_trends.apply(
        lambda row: classify_trend(row["oi_change"], row["price_change"]), axis=1
    )

    # --- drop first row (no diff available) ---
    merged = merged.iloc[1:].reset_index(drop=True)
    three_hr_trends = three_hr_trends.iloc[1:].reset_index(drop=True)

    # --- session summary (intraday vs daily net) ---
    session_df = nifty_df[
        (nifty_df["datetime"].dt.time >= pd.to_datetime("09:15").time()) &
        (nifty_df["datetime"].dt.time <= pd.to_datetime("15:30").time())
    ]
    day_open = session_df.iloc[0]["close"]
    day_close = session_df.iloc[-1]["close"]

    # intraday change
    net_price_change = day_close - day_open
    price_pct_change = (net_price_change / day_open) * 100

    # daily net change (prev close to today close, if available)
    prev_close = nifty_df.sort_values("datetime").iloc[0]["close"]
    full_close = nifty_df.sort_values("datetime").iloc[-1]["close"]
    daily_net_change = full_close - prev_close
    daily_pct_change = (daily_net_change / prev_close) * 100

    # OI net change (first vs last intraday snapshot)
    net_oi_change = merged["oi_change"].sum()
    oi_pct_change = (net_oi_change / merged["open_interest"].iloc[0]) * 100

    if net_price_change > 0 and net_oi_change > 0:
        final_trend = "Long Buildup"
    elif net_price_change > 0 and net_oi_change < 0:
        final_trend = "Short Covering"
    elif net_price_change < 0 and net_oi_change > 0:
        final_trend = "Short Buildup"
    elif net_price_change < 0 and net_oi_change < 0:
        final_trend = "Long Unwinding"
    else:
        final_trend = "Neutral"

    summary = {
        "Run Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Final Trend": final_trend,
        "Net OI Change": int(net_oi_change),
        "Net OI % Change": round(oi_pct_change, 2),
        "Intraday Change (pts)": round(net_price_change, 2),
        "Intraday % Change": round(price_pct_change, 2),
        "Daily Net Change (pts)": round(daily_net_change, 2),
        "Daily Net % Change": round(daily_pct_change, 2),
    }

    return merged[["datetime", "oi_change", "price_change", "trend"]], three_hr_trends, summary
