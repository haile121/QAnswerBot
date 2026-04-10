from dotenv import load_dotenv
load_dotenv()

import os
import json
import datetime
import logging
import gspread
from google.oauth2.service_account import Credentials

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# ---------------- LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- STATES ----------------
NAME, DEPT, PHONE, ANSWER = range(4)

# ---------------- ENV ----------------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN missing")

# ---------------- GOOGLE SHEETS ----------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds_json = os.getenv("GOOGLE_CREDS")
    if not creds_json:
        raise ValueError("❌ GOOGLE_CREDS missing")

    creds_info = json.loads(creds_json)

    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=SCOPES
    )

    client = gspread.authorize(creds)

except Exception as e:
    logger.error(f"Google Auth Error: {e}")
    raise

SHEET_ID = "1BttBP8LU4N66yq_Jfb1EN0__A5qzMRRRThMCKP2eFFM"
sheet = client.open_by_key(SHEET_ID).sheet1


# ---------------- SAFE RESET ----------------
def reset_user(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["step"] = None


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_user(context)

    await update.message.reply_text(
        "👋 Welcome!\n\nPlease enter your name:"
    )
    return NAME


# ---------------- NAME ----------------
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Enter valid name")
        return NAME

    context.user_data["name"] = text
    await update.message.reply_text("Enter department:")
    return DEPT


# ---------------- DEPT ----------------
async def get_dept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Enter valid department")
        return DEPT

    context.user_data["dept"] = text
    await update.message.reply_text("Enter phone number:")
    return PHONE


# ---------------- PHONE ----------------
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Enter valid phone")
        return PHONE

    context.user_data["phone"] = text
    await update.message.reply_text("Answer the question:")
    return ANSWER


# ---------------- ANSWER ----------------
async def get_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Enter valid answer")
        return ANSWER

    context.user_data["answer"] = text

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = context.user_data

    try:
        sheet.append_row([
            now,
            data.get("name"),
            data.get("dept"),
            data.get("phone"),
            data.get("answer"),
        ])
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await update.message.reply_text("❌ Failed to save data")
        return ConversationHandler.END

    reset_user(context)

    await update.message.reply_text("✅ Saved successfully!")
    return ConversationHandler.END


# ---------------- CANCEL ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_user(context)
    await update.message.reply_text("❌ Cancelled")
    return ConversationHandler.END


# ---------------- GLOBAL SAFETY HANDLER ----------------
async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    This fixes your exact issue:
    If Telegram restores weird state → we reset automatically
    """
    logger.warning("Unknown state hit → resetting user session")

    reset_user(context)

    await update.message.reply_text(
        "⚠️ Session reset.\nPlease type /start to begin again."
    )


# ---------------- ERROR HANDLER ----------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Error:", exc_info=context.error)


# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            DEPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_dept)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_answer)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,   
    )

    app.add_handler(conv)

    # 🔥 catch broken states / weird telegram resync issues
    app.add_handler(MessageHandler(filters.ALL, unknown_handler))

    app.add_error_handler(error_handler)

    print("🚀 Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()