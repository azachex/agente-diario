# Agente Diario — Railway

Briefing matutino automático a las 8:30h (España) vía Gmail.

## Contenido Fase 1
- 🌤️ Tiempo Zaragoza (3 días, Open-Meteo)
- 💰 Crypto: BTC, ETH, SOL, GRASS (CoinGecko)
- 🎱 Bonoloto — resultado y check de números

## Variables de entorno en Railway

| Variable | Descripción |
|---|---|
| `ANTHROPIC_API_KEY` | API key de Anthropic |
| `GMAIL_USER` | Tu Gmail (juan.diego.cuenca@gmail.com) |
| `GMAIL_APP_PASSWORD` | Contraseña de aplicación de Google (NO tu contraseña normal) |
| `DEST_EMAIL` | Email donde recibes el briefing |
| `COINGECKO_KEY` | Opcional — mejora el rate limit de CoinGecko |

## Cómo obtener la contraseña de aplicación de Gmail
1. Entra en myaccount.google.com
2. Seguridad → Verificación en dos pasos (debe estar activada)
3. Contraseñas de aplicaciones → Crear nueva → "Agente Diario"
4. Copia la contraseña de 16 caracteres que genera

## Despliegue en Railway
1. Sube esta carpeta a un repo de GitHub
2. railway.app → New Project → Deploy from GitHub
3. Añade las variables de entorno
4. ¡Listo!

## Probar manualmente
Para probar sin esperar a las 8:30, descomenta esta línea en main.py:
```python
# ejecutar_agente()
```
