import streamlit as st
import requests
import pandas as pd
import numpy as np
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
import matplotlib.pyplot as plt
import plotly.graph_objects as go

# API Keys and Constants
ETHERSCAN_API_KEY = "AMVFD2CJHWPZQ4XD9YCW8F3CRHRCPSHGM"
BSCSCAN_API_KEY = "GV2N1P84ZAG82WQ8KGSFQ8YR91SFWCQAKR"
SOLSCAN_API_BASE = "https://public-api.solscan.io"
GOPLUS_API = "https://api.gopluslabs.io/api/v1/token_security/"
DEXSCREENER = "https://api.dexscreener.com/latest/dex/pairs"
TELEGRAM_BOT_TOKEN = "7368632835:AAHUyizjntjpVa3yIweuxD9RjNoje4agKsI"
TELEGRAM_CHAT_ID = "6901755298"

# Function to detect blockchain network
def detect_chain(address):
    if address.startswith("0x") and len(address) == 42:
        return "ethereum"
    elif len(address) >= 32:
        return "solana"
    return None

# Function to fetch token information
def fetch_token_info(address, chain):
    try:
        if chain == "solana":
            url = f"{SOLSCAN_API_BASE}/token/meta?tokenAddress={address}"
            res = requests.get(url).json()
            if 'error' in res:
                st.error("Error fetching token info from Solana.")
                return None
            return {"name": res.get("name", "Solana Token"), "symbol": res.get("symbol", "SOLTKN"), "decimals": res.get("decimals", 9)}
        elif chain == "ethereum":
            url = f"https://api.etherscan.io/api?module=token&action=tokeninfo&contractaddress={address}&apikey={ETHERSCAN_API_KEY}"
            res = requests.get(url).json()
            if res.get("status") == "1":
                data = res['result'][0]
                return {"name": data.get("tokenName", "Unknown"), "symbol": data.get("tokenSymbol", "Unknown"), "decimals": int(data.get("tokenDecimal", 18))}
        elif chain == "binance-smart-chain":
            url = f"https://api.bscscan.com/api?module=token&action=tokeninfo&contractaddress={address}&apikey={BSCSCAN_API_KEY}"
            res = requests.get(url).json()
            if res.get("status") == "1":
                data = res['result'][0]
                return {"name": data.get("tokenName", "Unknown"), "symbol": data.get("tokenSymbol", "Unknown"), "decimals": int(data.get("tokenDecimal", 18))}
    except Exception as e:
        st.error(f"An error occurred: {e}")
    return None

# Function to audit token and get risk score
def audit_token(address, chain):
    try:
        url = f"{GOPLUS_API}{chain}?contract_addresses={address}"
        res = requests.get(url).json()
        data = list(res.get("result", {}).values())[0]
        risk = 100
        flags = {}
        for k, v in data.items():
            if isinstance(v, str) and v == "1":
                flags[k] = "❌ Bahaya"
                risk -= 5
            elif isinstance(v, str) and v == "0":
                flags[k] = "✅ Aman"
        return flags, max(risk, 0)
    except Exception as e:
        st.error(f"An error occurred during audit: {e}")
        return {}, 0

# Function to get token holders
def get_token_holders(address, chain):
    holders = []
    try:
        if chain == "solana":
            url = f"{SOLSCAN_API_BASE}/token/holders?tokenAddress={address}&limit=10"
            data = requests.get(url).json().get("data", [])
            for h in data:
                holders.append((h["owner"], h["amount"]))
        return holders
    except Exception as e:
        st.error(f"An error occurred while fetching holders: {e}")
        return []

# Function for entry/exit strategy
def entry_exit_strategy(risk, top_holder_percent):
    if risk >= 80 and top_holder_percent < 20:
        return "✅ Rekomendasi ENTRY: Aman dan distribusi merata"
    elif risk < 50 or top_holder_percent > 50:
        return "❌ Hindari ENTRY: Risiko tinggi atau distribusi buruk"
    return "⚠️ Tunggu sinyal tambahan"

# Function to estimate gas fees
def estimate_gas(chain):
    if chain == "ethereum":
        try:
            res = requests.get(f"https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={ETHERSCAN_API_KEY}").json()
            if res['status'] == '1':
                return res['result']
        except Exception as e:
            st.error(f"An error occurred while estimating gas: {e}")
    return {}

# Function to get price chart
def get_price_chart(address):
    try:
        res = requests.get(DEXSCREENER).json()
        for p in res['pairs']:
            if address.lower() in p['pairAddress'].lower():
                price = float(p['priceUsd'])
                volume = float(p['volume']['h24'])
                return price, volume
    except Exception as e:
        st.error(f"An error occurred while fetching price chart: {e}")
    return None, None

# Function to send Telegram notifications
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

# Function for AI risk scoring
def ai_risk_scoring(score, top_holder_percent, volume):
    if score > 80 and top_holder_percent < 20 and volume > 100000:
        return "🧠 AI: Aman untuk entry"
    elif score < 50 or top_holder_percent > 50:
        return "🧠 AI: Risiko tinggi, hindari"
    return "🧠 AI: Perlu analisis tambahan"

# Function to scan popular tokens
def scan_watchlist():
    res = requests.get(DEXSCREENER).json()
    hasil = []
    for token in res['pairs'][:10]:
        if float(token['liquidity']['usd']) > 50000:
            hasil.append({"pair": token['pairAddress'], "price": token['priceUsd'], "volume": token['volume']['h24']})
    return hasil

# Streamlit UI
st.set_page_config(layout="wide")
st.title("🧠 Crypto Coin Analyzer - Ultimate Pro Edition")

address = st.text_input("Paste Token Address:")
if address:
    chain = detect_chain(address)
    info = fetch_token_info(address, chain)
    if info:
        st.header(f"{info['name']} ({info['symbol']}) on {chain}")
        flags, score = audit_token(address, chain)
        st.subheader("🛡️ Audit Keamanan")
        for k, v in flags.items():
            st.write(f"{k}: {v}")
        st.metric("Skor Risiko", f"{score}/100")

        holders = get_token_holders(address, chain)
        if holders:
            df = pd.DataFrame(holders, columns=["Wallet", "Jumlah"])
            total = df['Jumlah'].sum()
            df['Persentase'] = df['Jumlah'] / total * 100
            st.subheader("📊 Distribusi Wallet Holder")
            st.dataframe(df)
            top = df.iloc[0]['Persentase']
            fig, ax = plt.subplots()
            ax.pie(df['Persentase'], labels=df['Wallet'], autopct='%1.1f%%')
            st.pyplot(fig)
        else:
            top = 100

        st.subheader("🤖 Strategi Entry/Exit")
        st.write(entry_exit_strategy(score, top))

        st.subheader("⛽ Estimasi Gas Fee")
        gas = estimate_gas(chain)
        st.write(gas)

        st.subheader("📈 Grafik Harga (Dexscreener)")
        price, volume = get_price_chart(address)
        if price:
            st.metric("Harga Saat Ini (USD)", f"${price:.4f}")
            st.metric("Volume 24h", f"${volume:,.0f}")
        else:
            st.warning("Harga tidak ditemukan.")

        st.subheader("🧠 AI Risk Analysis")
        st.write(ai_risk_scoring(score, top, volume if volume else 0))

        if score < 50:
            send_telegram(f"🚨 Token {info['name']} berisiko tinggi!")

        st.download_button("📤 Export ke Excel", data=df.to_csv().encode('utf-8'), file_name=f"{info['symbol']}_holders.csv")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Token Report: {info['name']}", ln=True)
        pdf.cell(200, 10, txt=f"Skor Risiko: {score}/100", ln=True)
        buffer = BytesIO()
        pdf.output(buffer)
        st.download_button("📄 Export PDF", buffer.getvalue(), file_name="report.pdf")

        st.success("✅ Analisis Selesai")

st.sidebar.header("🔎 Auto-Scan Token Populer")
for token in scan_watchlist():
    st.sidebar.write(f"📍 {token['pair']} | Harga: ${token['price']} | Volume: ${token['volume']:,.0f}")
