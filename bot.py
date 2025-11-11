import json, os
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
import gspread
from google.oauth2.service_account import Credentials
from data.token_key import TELEGRAM_TOKEN

# Detectar si estamos en Render
IS_RENDER = os.path.exists("/etc/secrets")

# Definir rutas seguras según el entorno
if IS_RENDER:
    BASE_PATH = "/etc/secrets"
else:
    BASE_PATH = "data"
    
# Cargar token desde el archivo secreto
import importlib.util
token_path = os.path.join(BASE_PATH, "token_key.py")
spec = importlib.util.spec_from_file_location("token_key", token_path)
token_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(token_module)
TELEGRAM_TOKEN = token_module.TELEGRAM_TOKEN


# ------------------ CONFIGURACIÓN ------------------
# Archivos JSON y credenciales
JSON_FILE = os.path.join(BASE_PATH, "clientes.json")
CREDENTIALS_FILE = os.path.join(BASE_PATH, "credentials_google.json")

# Configurar acceso a Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", 
          "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
gc = gspread.authorize(creds)
sheet = gc.open("Leads_ServiceboxBot").sheet1

# ------------------ ESTADOS ------------------
SERVICIO, PREGUNTAS, CONTACTO, OTRO_SERVICIO = range(4)

# ------------------ PREGUNTAS POR SERVICIO ------------------
FLUJOS = {
    "web": [
        "¿Qué tipo de web te interesa desarrollar? (por ejemplo: corporativa, blog, portfolio, etc.)",
        "¿Tienes ya los textos e imágenes preparados?",
        "¿Tienes alguna referencia o web que te guste? Si es así, compártela.",
        "¿Tienes una fecha límite o es flexible?  ¿cuándo te gustaría lanzarla?"
    ],
    "tienda": [
        "¿Ya tienes una tienda online o quieres crear una desde cero?",
        "¿Qué plataforma usas o te interesa? Si no sabes, puedo ayudarte a elegir.",
        "¿Cuántos productos tienes aproximadamente?",
        "¿Te gustaría incluir servicios adicionales (SEO, automatización, ERP)?"
    ],
    "facturacion": [
        "¿Qué tipo de empresa o autónomo eres?",
        "¿Ya usas algún software de facturación? Si es así, ¿cuál?",
        "¿Qué necesitas exactamente? (emitir facturas, gestionar clientes, etc.)",
        "¿Cuántas facturas emites al mes? Aproximadamente"
    ],
    "n8n": [
        "¿Has trabajado antes con herramientas de automatización? Si es así, ¿cuáles?",
        "¿Qué te gustaría automatizar? Mensajes, tareas repetitivas, integraciones...",
        "¿Con qué sistemas o apps quieres conectarlo? Dropbox, Google Sheets, CRM...",
        "¿Con qué frecuencia se ejecutaría la automatización? Diaria, semanal, en tiempo real..."
    ],
    "ia": [
        "¿Qué te gustaría que hiciera el agente de IA? (atención al cliente, generación de contenido, análisis de datos...)",
        "¿Dónde te gustaría implementarlo? (en tu web, en redes sociales, en una app...)",
        "¿Cuántas consultas tienes al día? Aproximadamente",
        "¿Deseas que se conecte con alguna fuente o sistema existente? CRM, base de datos..."
    ]
}

# ------------------ FUNCIONES ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await mostrar_servicios(update, context)
    return SERVICIO


async def mostrar_servicios(update, context):
    keyboard = [
        [InlineKeyboardButton("🌐 Desarrollo web", callback_data="web")],
        [InlineKeyboardButton("🛍️ Tiendas online", callback_data="tienda")],
        [InlineKeyboardButton("💼 Facturación electrónica", callback_data="facturacion")],
        [InlineKeyboardButton("⚙️ Automatismos (n8n)", callback_data="n8n")],
        [InlineKeyboardButton("🤖 Agentes IA", callback_data="ia")]
    ]
    if update.message:
        await update.message.reply_text(
            "👋 ¿En qué servicio estás interesado?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.callback_query.message.reply_text(
            "👋 ¿En qué servicio estás interesado?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def select_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["servicio"] = query.data
    context.user_data["respuestas"] = []
    context.user_data["pregunta_index"] = 0

    await query.message.reply_text(f"Perfecto, hablaremos sobre *{query.data}* 👇", parse_mode="Markdown")
    await query.message.reply_text(FLUJOS[query.data][0])
    return PREGUNTAS


async def handle_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    respuesta = update.message.text
    context.user_data["respuestas"].append(respuesta)
    index = context.user_data["pregunta_index"] + 1
    servicio = context.user_data["servicio"]

    if index < len(FLUJOS[servicio]):
        context.user_data["pregunta_index"] = index
        await update.message.reply_text(FLUJOS[servicio][index])
        return PREGUNTAS
    else:
        # Si ya tenemos contacto guardado, saltamos directamente al guardado
        if "contacto" in context.user_data and context.user_data["contacto"]:
            return await finalizar_guardado(update, context)
        else:
            await update.message.reply_text(
                "Perfecto 👌 Ahora necesito tus datos de contacto.\nPor favor, escribe tu *nombre completo*:",
                parse_mode="Markdown"
            )
            context.user_data["contacto"] = {}
            context.user_data["contacto_paso"] = "nombre"
            return CONTACTO


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    paso = context.user_data["contacto_paso"]

    if paso == "nombre":
        context.user_data["contacto"]["nombre"] = texto
        context.user_data["contacto_paso"] = "telefono"
        await update.message.reply_text("📞 Escribe tu número de teléfono:")
        return CONTACTO

    elif paso == "telefono":
        context.user_data["contacto"]["telefono"] = texto
        context.user_data["contacto_paso"] = "email"
        await update.message.reply_text("📧 Escribe tu correo electrónico:")
        return CONTACTO

    elif paso == "email":
        context.user_data["contacto"]["email"] = texto
        return await finalizar_guardado(update, context)


async def finalizar_guardado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_to_json(context.user_data)
    save_to_sheet(context.user_data)

    # Preguntar si desea otro servicio
    keyboard = [
        [
            InlineKeyboardButton("✅ Sí", callback_data="otro_si"),
            InlineKeyboardButton("❌ No", callback_data="otro_no"),
        ]
    ]
    await update.message.reply_text(
        "✅ ¡Gracias! Hemos guardado tu información.\n¿Quieres informarte sobre otro servicio?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return OTRO_SERVICIO


async def otro_servicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "otro_si":
        await query.message.reply_text("Perfecto 👍 Empecemos de nuevo.")
        await mostrar_servicios(update, context)
        return SERVICIO
    else:
        await query.message.reply_text("✅ ¡Gracias! por tu interés en Servicebox!  Hemos guardado tu información.\nNos pondremos en contacto contigo en breve.")
        return ConversationHandler.END


def save_to_json(data):
    servicio = data["servicio"]
    preguntas = FLUJOS[servicio]
    respuestas = data["respuestas"]
    respuestas_completas = "; ".join([f"{p} {r}" for p, r in zip(preguntas, respuestas)])

    entry = {
        "fecha": str(datetime.datetime.now()),
        "servicio": servicio,
        "respuestas": respuestas_completas,
        "nombre": data["contacto"]["nombre"],
        "telefono": data["contacto"]["telefono"],
        "email": data["contacto"]["email"]
    }

    if not os.path.exists(JSON_FILE) or os.stat(JSON_FILE).st_size == 0:
        clientes = []
    else:
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                clientes = json.load(f)
        except json.JSONDecodeError:
            clientes = []

    clientes.append(entry)
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(clientes, f, indent=4, ensure_ascii=False)


def save_to_sheet(data):
    servicio = data["servicio"]
    preguntas = FLUJOS[servicio]
    respuestas = data["respuestas"]
    respuestas_completas = "; ".join([f"{p} {r}" for p, r in zip(preguntas, respuestas)])

    sheet.append_row([
        str(datetime.datetime.now()),
        servicio,
        respuestas_completas,
        data["contacto"]["nombre"],
        data["contacto"]["telefono"],
        data["contacto"]["email"]
    ])


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Conversación cancelada. ¡Hasta luego!")
    return ConversationHandler.END


# ------------------ MAIN ------------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SERVICIO: [CallbackQueryHandler(select_service)],
            PREGUNTAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_questions)],
            CONTACTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact)],
            OTRO_SERVICIO: [CallbackQueryHandler(otro_servicio)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()


# --- Mantener el servicio activo en Render ---
import threading
from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram bot is running on Render!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    # Arranca el bot en un hilo
    threading.Thread(target=main).start()
    # Arranca el servidor Flask en el hilo principal
    run_flask()