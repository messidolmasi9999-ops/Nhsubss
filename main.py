import os
import secrets
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, abort, render_template_string
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Yeni token'ın eklendi (.env dosyasından da okunabilir, yoksa doğrudan bu tanımlıdır)
TOKEN = os.environ.get("BOT_TOKEN", "8629522039:AAFNcDE1kql3w2zMw3Z6DQWBL4DRmzN9MgY")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8080").rstrip("/")

app = Flask(__name__)
links = {}


def valid_url(value):
    try:
        parsed = urlparse(value)
        return parsed.scheme in ("http", "https") and bool(parsed.hostname)
    except Exception:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Bana bir video bağlantısı gönder, sana özel link oluşturalım."
    )


async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()

    if not valid_url(url):
        await update.message.reply_text(
            "Geçerli bir http:// veya https:// bağlantısı gönder."
        )
        return

    context.user_data["pending_url"] = url

    keyboard = [[
        InlineKeyboardButton(
            "🔗 Linke Dönüştür",
            callback_data="convert"
        )
    ]]

    await update.message.reply_text(
        "Bağlantın hazır. Dönüştürmek için butona bas:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    url = context.user_data.get("pending_url")

    if not url or not valid_url(url):
        await query.edit_message_text(
            "Önce yeni bir video bağlantısı gönder."
        )
        return

    code = secrets.token_urlsafe(12)
    links[code] = url
    result = f"{PUBLIC_URL}/v/{code}"

    await query.edit_message_text(
        f"✅ Bağlantın oluşturuldu:\n{result}"
    )


@app.get("/v/<code>")
def video_page(code):
    url = links.get(code)
    if not url:
        abort(404)

    return render_template_string("""
    <!doctype html>
    <html lang="tr">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta charset="utf-8">
    <title>Videonu görüntüle</title>
    <body style="font-family:Arial;max-width:700px;margin:35px auto;padding:16px">
      <h2>🎬 Videon hazır</h2>
      <video controls playsinline style="width:100%;max-height:65vh">
        <source src="{{ url }}">
        Tarayıcın bu videoyu doğrudan oynatamıyor.
      </video>
      <p>
        <a href="{{ url }}" target="_blank" rel="noopener noreferrer"
           style="display:inline-block;padding:12px 20px;background:#1677ff;
                  color:white;text-decoration:none;border-radius:8px">
          ⬇️ İndir / Videoyu aç
        </a>
      </p>
    </body>
    </html>
    """, url=url)


def main():
    import threading

    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080))),
        daemon=True,
    ).start()

    bot = Application.builder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CallbackQueryHandler(convert, pattern="^convert$"))
    bot.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)
    )
    bot.run_polling()


if __name__ == "__main__":
    main()
