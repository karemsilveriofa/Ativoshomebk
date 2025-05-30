import time
import requests
import telegram
from datetime import datetime, timedelta
import os

# === CONFIGURAÇÕES ===
API_KEY = os.getenv("API_KEY", "c95f42c34f934f91938f91e5cc8604a6")
INTERVAL = "1min"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7239698274:AAFyg7HWLPvXceJYDope17DkfJpxtU4IU2Y")
TELEGRAM_ID = os.getenv("TELEGRAM_ID", "6821521589")
bot = telegram.Bot(token=TELEGRAM_TOKEN)

ultima_entrada = None
preco_anterior = None

def bot_ativo():
    try:
        with open("status.txt", "r") as f:
            return f.read().strip().upper() == "ON"
    except:
        return True

def obter_ativo():
    try:
        with open("ativo.txt", "r") as f:
            return f.read().strip()
    except:
        return "EUR/USD"

def obter_dados(symbol):
    try:
        preco_url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={INTERVAL}&apikey={API_KEY}&outputsize=2"
        preco_data = requests.get(preco_url).json()
        if "values" not in preco_data:
            raise Exception(preco_data.get("message", "Erro ao obter preço"))

        preco = float(preco_data["values"][0]["close"])

        rsi_url = f"https://api.twelvedata.com/rsi?symbol={symbol}&interval={INTERVAL}&apikey={API_KEY}&time_period=14"
        rsi_data = requests.get(rsi_url).json()
        rsi = float(rsi_data["values"][0]["rsi"]) if "values" in rsi_data else None

        ma5_url = f"https://api.twelvedata.com/ma?symbol={symbol}&interval={INTERVAL}&apikey={API_KEY}&time_period=5&type=sma"
        ma20_url = f"https://api.twelvedata.com/ma?symbol={symbol}&interval={INTERVAL}&apikey={API_KEY}&time_period=20&type=sma"
        ma5_data = requests.get(ma5_url).json()
        ma20_data = requests.get(ma20_url).json()
        ma5 = float(ma5_data["values"][0]["ma"]) if "values" in ma5_data else None
        ma20 = float(ma20_data["values"][0]["ma"]) if "values" in ma20_data else None

        return preco, rsi, ma5, ma20
    except Exception as e:
        print("Erro ao obter dados:", e)
        return None, None, None, None

def enviar_sinal(mensagem):
    try:
        bot.send_message(chat_id=TELEGRAM_ID, text=mensagem)
        print("✅ Sinal enviado")
    except Exception as e:
        print("Erro ao enviar sinal:", e)

def monitorar():
    global preco_anterior, ultima_entrada

    while True:
        if not bot_ativo():
            print("⛔ Bot desligado")
            time.sleep(10)
            continue

        agora_utc = datetime.utcnow()
        proxima_entrada_utc = (agora_utc + timedelta(minutes=1)).replace(second=0, microsecond=0)
        segundos_faltando = (proxima_entrada_utc - agora_utc).total_seconds()

        if segundos_faltando <= 30:
            if ultima_entrada == proxima_entrada_utc:
                print("⚠️ Sinal já enviado para esta vela.")
                time.sleep(1)
                continue

            symbol = obter_ativo()
            preco, rsi, ma5, ma20 = obter_dados(symbol)

            if preco and rsi and ma5 and ma20:
                mensagem = f"📊 {symbol} ${preco:.5f}\n"

                if preco_anterior:
                    variacao = ((preco - preco_anterior) / preco_anterior) * 100
                    mensagem += f"🔄 Variação: {variacao:.3f}%\n"
                else:
                    variacao = 0
                    mensagem += "🟡 Iniciando monitoramento...\n"

                preco_anterior = preco

                entrada_brasilia = proxima_entrada_utc - timedelta(hours=3)
                horario_str = entrada_brasilia.strftime("%H:%M:%S")

                sinal = "⚪ SEM AÇÃO"

                if rsi < 45 or (ma5 > ma20 and variacao > 0.01):
                    sinal = f"🟢 COMPRA às {horario_str}"
                elif rsi > 55 or (ma5 < ma20 and variacao < -0.01):
                    sinal = f"🔴 VENDA às {horario_str}"

                mensagem += f"📈 RSI: {rsi:.2f}\n"
                mensagem += f"📉 MA5: {ma5:.5f} | MA20: {ma20:.5f}\n"
                mensagem += f"📍 SINAL: {sinal}"

                enviar_sinal(mensagem)
                ultima_entrada = proxima_entrada_utc

                time.sleep(35)
            else:
                print("❌ Dados incompletos. Pulando...")
                time.sleep(5)
        else:
            time.sleep(1)

monitorar()