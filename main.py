import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from gradio_client import Client
from deep_translator import GoogleTranslator

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

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

async def generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    await update.message.reply_text("⏳ جاري ترجمة الوصف وإنشاء الفيديو...")
    
    try:
        english_prompt = GoogleTranslator(source='auto', target='en').translate(user_prompt)
        
        # الاتصال بمساحة عمل نشطة (Space)
        ai_client = Client("fffiloni/LTX-Video", token=HF_TOKEN)
        result = ai_client.predict(
            prompt=english_prompt,
            negative_prompt="worst quality, low quality",
            frame_rate=25,
            api_name="/generate_video_1"
        )
        
        await update.message.reply_video(video=open(result, 'rb'))
    except Exception as e:
        # تجربة مسار احتياطي في حال اختلاف أسماء الدوال
        try:
            ai_client = Client("KingNish/LTX-Video", token=HF_TOKEN)
            result = ai_client.predict(prompt=english_prompt, api_name="/predict")
            await update.message.reply_video(video=open(result, 'rb'))
        except Exception as err:
            error_details = str(err)[:300]
            await update.message.reply_text(f"❌ حدث خطأ أثناء التوليد:\n{error_details}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_video))
    print("Bot is starting...")
    app.run_polling()
