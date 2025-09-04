
This repository provides a derivatives market analysis toolkit built using the ICICI Breeze API. It is designed to help retail traders and analysts gain actionable, data-driven insights into the options and futures market by combining real-time analytics, historical backtesting, and interactive visualization.
The project streamlines the process of fetching live and historical option chain data, calculating critical market indicators such as Put-Call Ratio (PCR), Max Pain, and Greeks, and visualizing Open Interest (OI) buildup, sentiment shifts, and risk metrics. By integrating alerts and monitoring utilities (like delta buffer checks, spot/futures trigger alerts, and IV sentiment dashboards), the toolkit aims to bring professional-grade analytics within the reach of independent traders.
Beyond real-time monitoring, the repository also supports backtesting frameworks to validate the reliability of common market theories (e.g., Max Pain vs. actual expiry prices) and to study how OI, PCR, and basis signals perform across historical data. The end goal is to establish a reusable, modular codebase that can serve as a foundation for more advanced trading models and intelligent advisory systems.

# Market Analysis with ICICI Breeze API

This repository provides a **derivatives market analysis toolkit** built using the **ICICI Breeze API**.  

## Features (Data being fetched from ICICI Breeze, and option chain from NSE website) 
- Option Chain analysis (PCR, Max Pain)
- Trend for Max Pain, PCR OI, PCR Vol over three months.
- OI Analysis by fetching data from NSE (Can be validate against the data from ICICI)
- OI Buildup analysis
- Volatility levels across different strikes across Puts and Calls.

## Setup
1. Clone this repo
2. Install dependencies:
   ```bash
   pip install -r requirements.txt

## Setup Breeze API Keys

This project uses the **ICICI Breeze API**.  
To run the notebooks, you need to provide your own API credentials.

1. Copy the template file:
   ```bash
   cp scripts/breeze_client_TEMPLATE.py scripts/breeze_client.py



---
This project is provided for educational and research purposes only.
It is not financial advice. Trading and investing involve risk, and you are solely responsible for your decisions.


