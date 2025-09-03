"""
nse_oi_analysis.py
---------------------------------
Fetches Option Chain data directly from NSE (no Breeze API),
transforms it into structured DataFrames, saves to Excel,
and provides sentiment + IV visualization utilities.
"""

import os
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ============== DIRECTORIES ==============
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Default save path
DEFAULT_SAVE_DIRECTORY = DATA_DIR

# NSE Option Chain endpoint
NSE_URL = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"


# ----------------------------
# Fetch option chain data
# ----------------------------
def fetch_option_chain():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }
    session = requests.Session()
    response = session.get(NSE_URL, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


# ----------------------------
# Transform option chain data
# ----------------------------
def transform_option_chain(data, expiry_date):
    records = []
    for item in data.get("records", {}).get("data", []):
        if item.get("expiryDate") == expiry_date:
            strike_price = item.get("strikePrice")
            call = item.get("CE", {})
            put = item.get("PE", {})
            records.append({
                "Call OI": call.get("openInterest"),
                "Change in Call OI": call.get("changeinOpenInterest"),
                "Call Volume": call.get("totalTradedVolume"),
                "Call IV": call.get("impliedVolatility"),
                "Strike Price": strike_price,
                "Put IV": put.get("impliedVolatility"),
                "Put Volume": put.get("totalTradedVolume"),
                "Change in Put OI": put.get("changeinOpenInterest"),
                "Put OI": put.get("openInterest"),
            })
    return pd.DataFrame(records)

# ----------------------------
# Calculate PCR and Max Pain
# ----------------------------
def calculate_pcr_max_pain(df):
    """Calculate PCR OI, PCR Volume, and Max Pain from NSE option chain DataFrame."""
    df = df.copy()
    df = df.fillna(0)

    # PCR OI
    total_put_oi = df["Put OI"].sum()
    total_call_oi = df["Call OI"].sum()
    pcr_oi = round(total_put_oi / total_call_oi, 2) if total_call_oi else 0

    # PCR Volume
    total_put_vol = df["Put Volume"].sum()
    total_call_vol = df["Call Volume"].sum()
    pcr_volume = round(total_put_vol / total_call_vol, 2) if total_call_vol else 0

    # Max Pain (loss minimization)
    losses = []
    for sp in df["Strike Price"].unique():
        call_loss = sum(max(0, sp - strike) * oi for strike, oi in zip(df["Strike Price"], df["Call OI"]))
        put_loss = sum(max(0, strike - sp) * oi for strike, oi in zip(df["Strike Price"], df["Put OI"]))
        losses.append((sp, call_loss + put_loss))

    max_pain = min(losses, key=lambda x: x[1])[0] if losses else None

    return {"PCR OI": pcr_oi, "PCR Volume": pcr_volume, "Max Pain": max_pain}


# ----------------------------
# Save to Excel
# ----------------------------
def save_to_excel(df, filename="OI_Nifty.xlsx"):
    output_path = os.path.join(DEFAULT_SAVE_DIRECTORY, filename)
    df.to_excel(output_path, index=False, sheet_name="OptionChain")
    return output_path

# ----------------------------
# Safe wrapper for fetch or load
# ----------------------------
def get_option_chain(expiry_date, filename=None, force_download=False):
    """
    Try to fetch fresh data from NSE. If it fails, load last saved Excel file.
    - expiry_date: string, e.g. "30-Sep-2025"
    - filename: optional custom Excel filename
    - force_download: True = always fetch, False = try file first
    """
    if filename is None:
        filename = f"OI_Nifty_{expiry_date}.xlsx"
    file_path = os.path.join(DEFAULT_SAVE_DIRECTORY, filename)

    # If file exists and force_download is False → load it
    if os.path.exists(file_path) and not force_download:
        print(f"📄 Loading existing file: {file_path}")
        return pd.read_excel(file_path, engine="openpyxl"), file_path

    # Else, try downloading
    try:
        print(f"🔄 Downloading fresh NSE data for {expiry_date}...")
        raw_data = fetch_option_chain()
        df = transform_option_chain(raw_data, expiry_date)
        if df.empty:
            raise ValueError("No data for expiry.")
        os.makedirs(DEFAULT_SAVE_DIRECTORY, exist_ok=True)
        save_to_excel(df, filename)
        print(f"✅ Data saved: {file_path}")
        return df, file_path
    except Exception as e:
        if os.path.exists(file_path):
            print(f"⚠️ NSE fetch failed ({e}). Loading last saved file instead: {file_path}")
            return pd.read_excel(file_path, engine="openpyxl"), file_path
        else:
            raise RuntimeError(f"❌ NSE fetch failed and no cached file found: {e}")

# ----------------------------
# Sentiment & IV Analysis
# ----------------------------
def analyze_sentiment_and_iv(file_path, india_vix):
    data = pd.read_excel(file_path)

    # Sentiment Analysis
    data["Call Sentiment"] = data["Change in Call OI"].apply(
        lambda x: "Bullish" if x > 0 else "Bearish" if x < 0 else "Neutral"
    )
    data["Put Sentiment"] = data["Change in Put OI"].apply(
        lambda x: "Bearish" if x > 0 else "Bullish" if x < 0 else "Neutral"
    )
    sentiment_summary = (
        data[["Call Sentiment", "Put Sentiment"]]
        .apply(pd.Series.value_counts)
        .fillna(0)
    )

    # 1. Sentiment Chart
    fig1 = go.Figure()
    for sentiment in sentiment_summary.index:
        fig1.add_trace(go.Bar(
            x=sentiment_summary.columns,
            y=sentiment_summary.loc[sentiment],
            name=sentiment
        ))
    fig1.update_layout(
        title="Nifty Sentiment Analysis (Calls vs Puts)",
        xaxis_title="Option Type",
        yaxis_title="Count",
        barmode="group",
        template="plotly_white"
    )

    # 2. Implied Volatility by Strike (all)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=data["Strike Price"], y=data["Call IV"],
        mode="lines+markers", name="Call IV"
    ))
    fig2.add_trace(go.Scatter(
        x=data["Strike Price"], y=data["Put IV"],
        mode="lines+markers", name="Put IV"
    ))
    fig2.add_hline(
        y=india_vix, line_dash="dot", line_color="red",
        annotation_text=f"India VIX ({india_vix:.2f})"
    )
    fig2.update_layout(
        title="Implied Volatility by Strike Price (All Strikes)",
        xaxis_title="Strike Price", yaxis_title="IV (%)",
        template="plotly_white"
    )

    # 3. Implied Volatility by Strike (non-zero IV only, multiples of 100)
    filtered = data[
        (data["Strike Price"] % 100 == 0) &
        (data["Call IV"] > 0) &
        (data["Put IV"] > 0)
    ]
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=filtered["Strike Price"], y=filtered["Call IV"],
        mode="lines+markers", name="Call IV"
    ))
    fig3.add_trace(go.Scatter(
        x=filtered["Strike Price"], y=filtered["Put IV"],
        mode="lines+markers", name="Put IV"
    ))
    fig3.add_hline(
        y=india_vix, line_dash="dot", line_color="red",
        annotation_text=f"India VIX ({india_vix:.2f})"
    )
    fig3.update_layout(
        title="Implied Volatility by Strike Price (Non-Zero IV, Multiples of 100)",
        xaxis_title="Strike Price", yaxis_title="IV (%)",
        template="plotly_white"
    )

    return fig1, fig2, fig3
