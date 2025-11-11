# 🤖 Servicebox Telegram Bot

Bot de Telegram para captar clientes interesados en servicios de Servicebox, almacenando información en **JSON** y **Google Sheets**, listo para desplegar en [Render.com](https://render.com) (plan gratuito) usando un Web Service.

---

## 📦 Funcionalidades

- Captura de leads interesados en:
  - 🌐 Desarrollo web
  - 🛍️ Tiendas online
  - 💼 Facturación electrónica
  - ⚙️ Automatismos (n8n)
  - 🤖 Agentes IA
- Conversación guiada por preguntas, usando **botones** e inputs.
- Almacena respuestas **junto con las preguntas** para mayor claridad.
- Guardado en:
  - JSON local
  - Google Sheets
- Permite registrar múltiples servicios por cliente **sin pedir sus datos personales otra vez**.
- Compatible con **Render.com plan gratuito**, manteniendo el bot activo mediante un servidor Flask dummy.

---

## ⚙️ Requisitos

- Python >= 3.14
- Librerías necesarias (listadas en `requirements.txt`):

```text
anyio==4.11.0
cachetools==6.2.1
certifi==2025.10.5
charset-normalizer==3.4.4
google-auth==2.41.1
google-auth-oauthlib==1.2.3
gspread==6.2.1
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
idna==3.11
oauthlib==3.3.1
pyasn1==0.6.1
pyasn1_modules==0.4.2
python-telegram-bot==22.5
requests==2.32.5
requests-oauthlib==2.0.0
rsa==4.9.1
sniffio==1.3.1
urllib3==2.5.0