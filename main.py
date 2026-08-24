import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from gradio_client import Client
from deep_translator import GoogleTranslator

# تشغيل منفذ خفيف لإبقاء Render نشطاً
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive")

def run_web_port():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_port, daemon=True).start()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

# رسالة الترحيب عند بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "مرحباً بك في صانع الفيديوهات! 🎬✨\n\n"
        "اكتب لي وصف الفيديو الذي تريد إنشاءه بأي لغة:\n"
        "• العربية 🇸🇦\n"
        "• الفرنسية 🇫🇷\n"
        "• الإنجليزية 🇬🇧\n\n"
        "مثال: `قط يصطاد السمك في النهر`"
    )
    await update.message.reply_text(welcome_text)

# معالجة طلبات الفيديوهات
async def generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    await update.message.reply_text("⏳ تم إرسال الطلب لطابور المعالجة..\nيرجى الانتظار من 2 إلى 4 دقائق لتوليد الفيديو 🎬")
    
    try:
        # ترجمة الوصف إلى الإنجليزية تلقائياً
        english_prompt = GoogleTranslator(source='auto', target='en').translate(user_prompt)
        
        # الاتصال بالنموذج
        ai_client = Client("multimodalart/LTX-Video", token=HF_TOKEN)
        result = ai_client.predict(
            prompt=english_prompt,
            negative_prompt="worst quality, low quality, blurry",
            api_name="/generate_video"
        )
        
        await update.message.reply_video(video=open(result, 'rb'), caption="✨ تم إنشاء الفيديو بنجاح!")
    except Exception as e:
        error_details = str(e)[:200]
        await update.message.reply_text(f"❌ السيرفر مشغول جداً حالياً أو انتهت مهلة الانتظار. أعد المحاولة بعد قليل.\n{error_details}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_video))
    print("Bot is running...")
    app.run_polling()
