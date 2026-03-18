"""
Minimal bot — sends the Mini App button.
Set WEBAPP_URL to your public HTTPS URL (e.g. ngrok).
"""
import asyncio
import logging

from telegram import Update, MenuButtonWebApp, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

from config import BOT_TOKEN, WEBAPP_URL

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🃏 Открыть клуб", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    await update.message.reply_text(
        "👋 Добро пожаловать в покерный клуб!",
        reply_markup=kb,
    )


async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))

    # Set persistent menu button
    async with app:
        await app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="🃏 Клуб", web_app=WebAppInfo(url=WEBAPP_URL))
        )
        await app.initialize()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await app.start()
        logging.info("Bot started. Mini App: %s", WEBAPP_URL)
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
