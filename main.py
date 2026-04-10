from dotenv import load_dotenv
load_dotenv()

import os
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
    ConversationHandler
)

# ---------------- LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- STATES ----------------
NAME, DEPT, PHONE, ANSWER = range(4)

# ---------------- BOT TOKEN ----------------
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing in environment variables!")

# ---------------- GOOGLE SHEETS AUTH ----------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds = Credentials.from_service_account_file(
        "credentials.json",
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
except Exception as e:
    logger.error(f"Google Auth Error: {e}")
    raise

# ⚠️ PUT YOUR SHEET ID HERE
SHEET_ID = "1BttBP8LU4N66yq_Jfb1EN0__A5qzMRRRThMCKP2eFFM"

try:
    sheet = client.open_by_key(SHEET_ID).sheet1
except Exception as e:
    logger.error(f"Sheet Open Error: {e}")
    raise


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "Let's start the form:\n"
        "👤 Please enter your name"
    )
    return NAME


# ---------------- NAME ----------------
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if not text:
        await update.message.reply_text("⚠️ Please enter a valid name.")
        return NAME

    context.user_data["name"] = text.strip()
    await update.message.reply_text("🏫 Enter your department:")
    return DEPT


# ---------------- DEPT ----------------
async def get_dept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if not text:
        await update.message.reply_text("⚠️ Please enter a valid department.")
        return DEPT

    context.user_data["dept"] = text.strip()
    await update.message.reply_text("📞 Enter your phone number:")
    return PHONE


# ---------------- PHONE ----------------
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if not text:
        await update.message.reply_text("⚠️ Please enter a valid phone number.")
        return PHONE

    context.user_data["phone"] = text.strip()

    await update.message.reply_text(
        "❓ Now answer the question:\n\n"
        "👉 You can type anything (1 / 2 / 3 or full sentence)"
    )
    return ANSWER


# ---------------- ANSWER ----------------
async def get_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if not text:
        await update.message.reply_text("⚠️ Please enter a valid answer.")
        return ANSWER

    context.user_data["answer"] = text.strip()

    data = context.user_data
    time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        sheet.append_row([
            time,
            data.get("name", ""),
            data.get("dept", ""),
            data.get("phone", ""),
            data.get("answer", "")
        ], value_input_option="USER_ENTERED")

    except Exception as e:
        logger.error(f"Sheet Write Error: {e}")
        await update.message.reply_text("❌ Error saving data. Please try again later.")
        return ConversationHandler.END

    await update.message.reply_text(
        "✅ Thank you!\nYour response has been saved successfully."
    )

    return ConversationHandler.END


# ---------------- CANCEL ----------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled successfully.")
    return ConversationHandler.END


# ---------------- ERROR HANDLER ----------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling update:", exc_info=context.error)


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
    )

    app.add_handler(conv)

    # global error handler
    app.add_error_handler(error_handler)

    print("🚀 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()