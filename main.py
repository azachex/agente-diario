import os
import schedule
import time
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import anthropic

# ── Config ────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
GMAIL_USER        = os.environ.get("GMAIL_USER")        # tu email
GMAIL_PASSWORD    = os.environ.get("GMAIL_APP_PASSWORD") # contraseña de aplicación
DEST_EMAIL        = os.environ.get("DEST_EMAIL")         # dónde recibes el briefing
COINGECKO_KEY     = os.environ.get("COINGECKO_KEY", "")  # opcional, mejora rate limit

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

BONOLOTO = [2, 4, 15, 23, 33, 41]

# ── Datos: Crypto ─────────────────────────────────────────────────────────────
def get_crypto():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "bitcoin,ethereum,solana,grass",
            "vs_currencies": "eur,usd",
            "include_24hr_change": "true"
        }
        headers = {"x-cg-demo-api-key": COINGECKO_KEY} if COINGECKO_KEY else {}
        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        result = {}
        for coin_id, name in [("bitcoin","BTC"),("ethereum","ETH"),("solana","SOL"),("grass","GRASS")]:
            if coin_id in data:
                result[name] = {
                    "eur": data[coin_id].get("eur", "N/A"),
                    "usd": data[coin_id].get("usd", "N/A"),
                    "change_24h": data[coin_id].get("eur_24h_change", 0)
                }
        return result
    except Exception as e:
        return {"error": str(e)}

# ── Datos: Tiempo Zaragoza ────────────────────────────────────────────────────
def get_weather():
    try:
        # Open-Meteo, gratis sin key
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 41.65,
            "longitude": -0.89,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
            "hourly": "temperature_2m,precipitation_probability",
            "current_weather": True,
            "timezone": "Europe/Madrid",
            "forecast_days": 3
        }
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ── Datos: Bonoloto ───────────────────────────────────────────────────────────
def get_bonoloto():
    try:
        # API pública de resultados lotería España
        r = requests.get(
            "https://www.loteriasyapuestas.es/servicios/buscadorSorteos",
            params={"game_id": "BONO", "celebrado": "true", "num_pages": 1},
            timeout=10
        )
        sorteos = r.json()
        if sorteos:
            ultimo = sorteos[0]
            fecha = ultimo.get("fecha_sorteo", "")
            numeros_str = ultimo.get("combinacion", "")
            complementario = ultimo.get("complementario", "")
            reintegro = ultimo.get("reintegro", "")
            # parsear números
            try:
                numeros = [int(n) for n in numeros_str.split("-") if n.strip().isdigit()]
            except:
                numeros = []
            aciertos = [n for n in BONOLOTO if n in numeros]
            return {
                "fecha": fecha,
                "numeros": numeros,
                "complementario": complementario,
                "reintegro": reintegro,
                "mis_numeros": BONOLOTO,
                "aciertos": aciertos,
                "num_aciertos": len(aciertos)
            }
    except Exception as e:
        pass
    return {"error": "No se pudo obtener el resultado"}

# ── Claude: genera el briefing ────────────────────────────────────────────────
def generar_briefing(crypto, weather, bonoloto):
    hoy = datetime.now().strftime("%A %d de %B de %Y")

    # Preparar resumen de datos para Claude
    crypto_txt = ""
    for name, vals in crypto.items():
        if "error" not in vals:
            arrow = "▲" if vals["change_24h"] > 0 else "▼"
            color = "verde" if vals["change_24h"] > 0 else "rojo"
            crypto_txt += f"- {name}: {vals['eur']:,.0f}€ / ${vals['usd']:,.0f} ({arrow}{abs(vals['change_24h']):.1f}% 24h)\n"

    weather_txt = ""
    if "error" not in weather and "daily" in weather:
        d = weather["daily"]
        for i in range(min(3, len(d["time"]))):
            weather_txt += f"- {d['time'][i]}: max {d['temperature_2m_max'][i]}°C / min {d['temperature_2m_min'][i]}°C, lluvia {d['precipitation_sum'][i]}mm\n"
        if "current_weather" in weather:
            cw = weather["current_weather"]
            weather_txt = f"Ahora mismo: {cw.get('temperature')}°C, viento {cw.get('windspeed')} km/h\n" + weather_txt

    bonoloto_txt = ""
    if "error" not in bonoloto:
        bonoloto_txt = f"Sorteo {bonoloto['fecha']}: {'-'.join(map(str, bonoloto['numeros']))} C:{bonoloto['complementario']} R:{bonoloto['reintegro']}\n"
        bonoloto_txt += f"Tus números: {'-'.join(map(str, BONOLOTO))}\n"
        if bonoloto['num_aciertos'] == 0:
            bonoloto_txt += "Sin aciertos esta vez."
        else:
            bonoloto_txt += f"¡{bonoloto['num_aciertos']} aciertos! Números: {bonoloto['aciertos']}"

    prompt = f"""Eres el asistente personal de JuanDiego, director comercial de MAS SEEDS en Zaragoza.
Hoy es {hoy}. Genera su briefing matutino en español con tono directo, cercano y algo de humor.

DATOS DISPONIBLES:

CRYPTO:
{crypto_txt if crypto_txt else "No disponible"}

TIEMPO ZARAGOZA (3 días):
{weather_txt if weather_txt else "No disponible"}

BONOLOTO:
{bonoloto_txt if bonoloto_txt else "No disponible"}

Genera un briefing en HTML bien formateado con:
1. Saludo corto con la fecha
2. Sección TIEMPO — resumen del día y previsión 3 días
3. Sección CRYPTO — estado BTC (alerta si está cerca de 58.000$ soporte o 65.000$ resistencia), ETH, SOL, GRASS
4. Sección BONOLOTO — resultado del último sorteo y si hay aciertos
5. Cierre motivador de una línea

Usa HTML limpio con colores. Verde para subidas/buenas noticias, rojo para bajadas/alertas.
El email debe verse bien en móvil. Usa inline CSS."""

    respuesta = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    return respuesta.content[0].text

# ── Email ─────────────────────────────────────────────────────────────────────
def enviar_email(html_content):
    hoy = datetime.now().strftime("%d/%m/%Y")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"☀️ Briefing Diario — {hoy}"
    msg["From"]    = GMAIL_USER
    msg["To"]      = DEST_EMAIL

    parte_html = MIMEText(html_content, "html")
    msg.attach(parte_html)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, DEST_EMAIL, msg.as_string())
    print(f"[{datetime.now()}] Email enviado correctamente")

# ── Tarea principal ───────────────────────────────────────────────────────────
def ejecutar_agente():
    print(f"[{datetime.now()}] Iniciando agente diario...")
    try:
        crypto   = get_crypto()
        weather  = get_weather()
        bonoloto = get_bonoloto()
        html     = generar_briefing(crypto, weather, bonoloto)
        enviar_email(html)
    except Exception as e:
        print(f"[{datetime.now()}] ERROR: {e}")

# ── Scheduler ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Agente Diario iniciado. Próxima ejecución: 08:30 hora Madrid")
    schedule.every().day.at("07:30").do(ejecutar_agente)  # 07:30 UTC = 08:30 España
    # Descomenta la siguiente línea para probar al arrancar:
    ejecutar_agente()
    while True:
        schedule.run_pending()
        time.sleep(30)
