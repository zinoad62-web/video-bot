import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from gradio_client import Client
from deep_translator import GoogleTranslator

# 1. خادم وهمي لإبقاء Render نشطاً
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

# 2. واجهة الترحيب عند بدء البوت /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "مرحباً بك! 👋🎬\n\n"
        "أنا بوت صناعة الفيديوهات بالذكاء الاصطناعي.\n"
        "أرسل لي وصف الفيديو الذي تتخيله بـ **العربية**، **الفرنسية**، أو **الإنجليزي** وسأقوم بإنشائه لك!"
    )
    await update.message.reply_text(welcome_message)

# 3. دالة الاتصال بـ Hugging Face داخل خيط منفصل (Thread)
def process_video_generation(prompt_text, token):
    english_prompt = GoogleTranslator(source='auto', target='en').translate(prompt_text)
    ai_client = Client("multimodalart/LTX-Video", token=token)
    return ai_client.predict(
        prompt=english_prompt,
        negative_prompt="worst quality, low quality",
        api_name="/generate_video"
    )

# 4. معالجة الطلب بمهلة زمنية محددة
async def generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    await update.message.reply_text("⏳ تم إرسال الطلب، جاري التوليد (يرجى الانتظار من 1 إلى 3 دقائق)...")
    
    try:
        # تشغيل العملية مع مهلة زمنية 180 ثانية لعدم التعليق
        result = await asyncio.wait_for(
            asyncio.to_thread(process_video_generation, user_prompt, HF_TOKEN),
            timeout=180.0
        )
        await update.message.reply_video(video=open(result, 'rb'), caption="✨ تم إنشاء الفيديو بنجاح!")
    except asyncio.TimeoutError:
        await update.message.reply_text("⚠️ السيرفر مشغول جداً وطابور الانتظار طويل. يرجى إرسال الطلب مرة أخرى الآن.")
    except Exception as e:
        err_msg = str(e)[:200]
        await update.message.reply_text(f"❌ حدث خطأ أثناء التوليد:\n{err_msg}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_video))
    print("Bot is running...")
    app.run_polling()
