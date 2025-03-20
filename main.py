import requests
import time
import telebot
import traceback
import json
from datetime import datetime
import plotly.graph_objects as go
import plotly.io as pio
import os
from flask import Flask, render_template
import threading

# Configura tu bot de Telegram
TOKEN = "7907463563:AAHQ6WHQVfCaX8xYcxlE-82zQHqxMPvRdXU"
import logging

logger = telebot.logger
telebot.logger.setLevel(logging.ERROR)
bot = telebot.TeleBot(TOKEN)

# Archivos y variables globales
SUSCRIPTORES_ARCHIVO = "suscriptores.json"
MENSAJE_CONTADOR = 0
mensaje_lock = threading.Lock()


def cargar_suscriptores():
    try:
        with open(SUSCRIPTORES_ARCHIVO, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        suscriptores = ["5721222937"]
        guardar_suscriptores(suscriptores)
        return suscriptores


def guardar_suscriptores(suscriptores):
    with open(SUSCRIPTORES_ARCHIVO, 'w') as f:
        json.dump(suscriptores, f)


suscriptores = cargar_suscriptores()


def registrar_error(mensaje):
    with open("error_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {mensaje}\n")


def obtener_precio_wbera():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=wrapped-bera&vs_currencies=usd&include_24hr_change=true"
    try:
        respuesta = requests.get(url).json()
        print("📊 Respuesta de la API: ", respuesta)
        if not respuesta:
            registrar_error("❌ Respuesta vacía de la API.")
            return None, None
        if 'wrapped-bera' in respuesta:
            precio = respuesta['wrapped-bera']['usd']
            cambio_24h = respuesta['wrapped-bera']['usd_24h_change']
            return precio, cambio_24h
        else:
            error_msg = "❌ Error: 'wrapped-bera' no está en la respuesta."
            print(error_msg)
            registrar_error(error_msg + f" Respuesta: {respuesta}")
            return None, None
    except Exception as e:
        error_msg = f"❌ Error al realizar la solicitud a la API: {e}\n{traceback.format_exc()}"
        print(error_msg)
        registrar_error(error_msg)
        return None, None


def obtener_datos_velas():
    # Reemplazar con tu API para obtener datos de velas de 1 hora
    # Ejemplo: usando una API ficticia
    return [
        {
            'time': '2024-10-27 10:00',
            'open': 10,
            'high': 12,
            'low': 9,
            'close': 11
        },
        {
            'time': '2024-10-27 11:00',
            'open': 11,
            'high': 13,
            'low': 10,
            'close': 12
        },
        {
            'time': '2024-10-27 12:00',
            'open': 12,
            'high': 14,
            'low': 11,
            'close': 13
        },
        # ... Agregar más datos
    ]


def crear_grafico_velas():
    try:
        data = obtener_datos_velas()
        if not data:
            return None

        fig = go.Figure(data=[
            go.Candlestick(x=[item['time'] for item in data],
                           open=[item['open'] for item in data],
                           high=[item['high'] for item in data],
                           low=[item['low'] for item in data],
                           close=[item['close'] for item in data])
        ])

        pio.orca.config.executable = "/usr/bin/orca"  # Specify path if needed. Adjust accordingly to your system.
        chart_file = 'bera_chart.png'
        pio.write_image(fig, chart_file)
        return chart_file
    except Exception as e:
        registrar_error(f"Error al crear el gráfico: {e}")
        return None


def enviar_mensaje():
    with mensaje_lock:
        precio, cambio_24h = obtener_precio_wbera()
        if precio is not None and cambio_24h is not None:
            emoji = "🚀" if cambio_24h >= 9 else ""
            mensaje = f"$ {precio:.2f}\n Last 24h: [{cambio_24h:.2f}%] {emoji}"

            # Enviar a todos los suscriptores
            for chat_id in suscriptores:
                try:
                    bot.send_message(chat_id, mensaje)
                    print(f"✅ Mensaje enviado a {chat_id}: {mensaje}")

                    global MENSAJE_CONTADOR
                    MENSAJE_CONTADOR += 1
                    if MENSAJE_CONTADOR >= 20:
                        MENSAJE_CONTADOR = 0
                        chart_file = crear_grafico_velas()
                        if chart_file:
                            with open(chart_file, 'rb') as photo:
                                bot.send_photo(
                                    chat_id,
                                    photo,
                                    caption='Gráfico BERA/USD última hora')
                                os.remove(chart_file)  # Delete after sending
                except Exception as e:
                    print(f"❌ Error al enviar mensaje a {chat_id}: {e}")

        else:
            print(
                "⚠️ No se pudo enviar el mensaje. Revisa la respuesta de la API."
            )


@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    chat_id = str(message.chat.id)
    print(
        f"📱 Usuario {message.from_user.username} ({chat_id}) usó comando /start o /help"
    )

    if chat_id not in suscriptores:
        suscriptores.append(chat_id)
        guardar_suscriptores(suscriptores)
        print(
            f"👤 Nuevo suscriptor: {chat_id} (Total suscriptores: {len(suscriptores)})"
        )

    commands_text = """
BERA price tracking bot. Sending updates every 5 minutes. You can use /buy or /sell to get a link to trade your tokens on BeraChain!

*Available Commands:* 📋
• /start - Subscribe to price updates
• /stop - Unsubscribe from updates
• /price - Get current WBERA price
• /help - Show this help
"""
    bot.send_message(message.chat.id, commands_text, parse_mode="Markdown")


@bot.message_handler(commands=['stop'])
def handle_stop(message):
    chat_id = str(message.chat.id)

    if chat_id in suscriptores:
        suscriptores.remove(chat_id)
        guardar_suscriptores(suscriptores)
        bot.reply_to(
            message,
            "You have unsubscribed from BERA price updates. Use /start to subscribe again."
        )
        print(f"👋 Suscriptor eliminado: {chat_id}")
    else:
        bot.reply_to(message, "You are not subscribed to updates.")


@bot.message_handler(commands=['buy', 'sell'])
def handle_buy_sell(message):
    bot.send_message(
        message.chat.id,
        "You can buy and sell any of your Berachain tokens with SigmaBot! https://t.me/Sigma_buyBot?start=ref=5721222937"
    )


@bot.message_handler(commands=['price'])
def handle_price(message):
    print(
        f"📱 Usuario {message.from_user.username} ({message.chat.id}) solicitó el precio"
    )
    precio, cambio_24h = obtener_precio_wbera()
    if precio is not None and cambio_24h is not None:
        emoji = "🚀" if cambio_24h >= 9 else ""
        mensaje = f"💰 *Current BERA Price*\n$ {precio:.2f}\n📈 Last 24h: [{cambio_24h:.2f}]% {emoji}"
        bot.send_message(message.chat.id, mensaje, parse_mode="Markdown")
        print(f"✅ Precio enviado: ${precio:.2f} (cambio: {cambio_24h:.2f}%)")
    else:
        bot.send_message(
            message.chat.id,
            "❌ Sorry, I couldn't get the current price. Please try again later."
        )
        print("❌ Error al obtener el precio")


# Comando para mostrar información sobre BERA
@bot.message_handler(commands=['info'])
def handle_info(message):
    info_text = """
*What is Berachain?* 🐻

Berachain is an EVM-compatible Layer 1 blockchain built using the Cosmos SDK. It uses a novel consensus mechanism called Proof of Liquidity (PoL).

*Key Features:*
• Fast transaction speeds
• Low fees
• EVM compatibility
• DeFi focused ecosystem

*Official Links:*
• Website: https://berachain.com
• Twitter: https://twitter.com/berachain
• Discord: https://discord.gg/berachain
    """
    bot.send_message(message.chat.id,
                     info_text,
                     parse_mode="Markdown",
                     disable_web_page_preview=True)


# Comando para mostrar estadísticas de mercado
@bot.message_handler(commands=['stats'])
def handle_stats(message):
    try:
        url = "https://api.coingecko.com/api/v3/coins/wrapped-bera"
        respuesta = requests.get(url).json()

        market_data = respuesta.get('market_data', {})
        if market_data:
            current_price = market_data.get('current_price',
                                            {}).get('usd', 'N/A')
            market_cap = market_data.get('market_cap', {}).get('usd', 'N/A')
            total_volume = market_data.get('total_volume',
                                           {}).get('usd', 'N/A')
            high_24h = market_data.get('high_24h', {}).get('usd', 'N/A')
            low_24h = market_data.get('low_24h', {}).get('usd', 'N/A')

            stats_text = f"""
*BERA Market Statistics* 📊

• Current Price: ${current_price:,}
• Market Cap: ${market_cap:,}
• 24h Trading Volume: ${total_volume:,}
• 24h High: ${high_24h:,}
• 24h Low: ${low_24h:,}
            """
            bot.send_message(message.chat.id,
                             stats_text,
                             parse_mode="Markdown")
        else:
            bot.send_message(
                message.chat.id,
                "❌ Sorry, I couldn't get the market statistics. Please try again later."
            )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")


# Lista de comandos disponibles
@bot.message_handler(commands=['commands', 'help'])
def handle_commands(message):
    commands_text = """
*Available Commands:* 📋

• /start - Subscribe to price updates
• /stop - Unsubscribe from updates
• /price - Get current WBERA price
• /stats - View market statistics
• /info - Learn about Berachain
• /buy or /sell - Get trading link
• /interval [minutes] - Change update frequency
• /charts - View BERA price chart
• /volume - Show trading volume
• /holdings - Check your holdings
• /swap - Get swap info
• /gas - Check gas prices
• /supply - View circulating supply
• /staking - Get staking info
• /commands - Show this list
    """
    bot.send_message(message.chat.id, commands_text, parse_mode="Markdown")


@bot.message_handler(commands=['charts'])
def handle_charts(message):
    bot.reply_to(
        message,
        "📊 BERA Price Chart:\nhttps://dexscreener.com/berachain/0x8c56017b172226fe024dea197748fc1eaccc82b1"
    )


@bot.message_handler(commands=['volume'])
def handle_volume(message):
    bot.reply_to(
        message,
        "📈 Trading Volume:\nhttps://dexscreener.com/berachain/0x8c56017b172226fe024dea197748fc1eaccc82b1"
    )


@bot.message_handler(commands=['holdings'])
def handle_holdings(message):
    bot.reply_to(message, "💼 Check your holdings:\nhttps://beratrail.io/")


@bot.message_handler(commands=['swap'])
def handle_swap(message):
    bot.reply_to(message, "🔄 Swap BERA:\nhttps://artio.bex.berachain.com/")


@bot.message_handler(commands=['gas'])
def handle_gas(message):
    bot.reply_to(message,
                 "⛽ Check current gas prices:\nhttps://berachain.com/gas")


@bot.message_handler(commands=['supply'])
def handle_supply(message):
    bot.reply_to(
        message,
        "💰 View BERA supply:\nhttps://beratrail.io/token/0x0000000000000000000000000000000000000000"
    )


@bot.message_handler(commands=['staking'])
def handle_staking(message):
    bot.reply_to(message,
                 "🏦 Staking information:\nhttps://www.berachain.com/staking")


# Ejecutar el primer mensaje al inicio
#enviar_mensaje()

# Configurar comandos del bot
bot.set_my_commands([
    telebot.types.BotCommand("/price", "Get current BERA price"),
    telebot.types.BotCommand("/stats", "View market statistics"),
    telebot.types.BotCommand("/info", "Learn about Berachain"),
    telebot.types.BotCommand("/buy", "Get link to buy tokens"),
    telebot.types.BotCommand("/sell", "Get link to sell tokens"),
    telebot.types.BotCommand("/interval", "Change update frequency"),
    telebot.types.BotCommand("/commands", "Show all available commands"),
    telebot.types.BotCommand("/start", "Subscribe to price updates"),
    telebot.types.BotCommand("/stop", "Unsubscribe from updates")
])

# Flask app
app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


def run_flask():
    app.run(host='0.0.0.0', port=8080)


def run_bot():
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"❌ Error en el bot: {e}")
            time.sleep(10)


def run_scheduler():
    last_run_minute = -1
    while True:
        try:
            current_minute = datetime.now().minute
            if current_minute % 5 == 0 and current_minute != last_run_minute:
                enviar_mensaje()
                last_run_minute = current_minute
            time.sleep(30)  # Revisar cada 30 segundos
        except Exception as e:
            print(f"❌ Error en el scheduler: {e}")
            time.sleep(5)


if __name__ == "__main__":
    # Iniciar Flask en un thread separado
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Iniciar el bot en un thread separado
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # Iniciar el scheduler en un thread separado
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    # Loop principal para mantener el programa vivo
    while True:
        time.sleep(60)


@app.route('/status')
def status():
    return "El bot está en funcionamiento y listo para enviar actualizaciones."
