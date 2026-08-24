import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from gradio_client import Client
from deep_translator import GoogleTranslator

# فتح منفذ الويب فوراً لإرضاء Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active")

def run_web_port():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_port, daemon=True).start()

# إعدادات البوت
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

async def generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    await update.message.reply_text("⏳ جاري ترجمة الوصف وإنشاء الفيديو...")
    
    try:
        english_prompt = GoogleTranslator(source='auto', target='en').translate(user_prompt)
        ai_client = Client("Lightricks/LTX-Video", token=HF_TOKEN)
        result = ai_client.predict(prompt=english_prompt, api_name="/predict")
        await update.message.reply_video(video=open(result, 'rb'))
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("السيرفر مشغول حالياً، يرجى المحاولة بعد قليل.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_video))
    print("Bot is starting...")
    app.run_polling()
