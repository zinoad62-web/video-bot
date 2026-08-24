import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from gradio_client import Client
from deep_translator import GoogleTranslator

# 1. خادم ويب مصغر لإبقاء Render نشطاً
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

# 2. رسالة الترحيب /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "مرحباً بك في بوت صناعة الفيديوهات! 🎬✨\n\n"
        "أرسل لي وصف الفيديو الذي تتخيله بـ **العربية**، **الفرنسية**، أو **الإنجليزي** وسأقوم بإنشائه لك!"
    )
    await update.message.reply_text(welcome_message)

# 3. قائمة سيرفرات الذكاء الاصطناعي المتاحة
SPACES_TO_TRY = [
    ("damo-vilab/modelscope-text-to-video-synthesis", "/predict"),
    ("ByteDance/AnimateDiff", "/generate")
]

def process_video_generation(prompt_text, token):
    # ترجمة الوصف إلى الإنجليزية تلقائياً
    english_prompt = GoogleTranslator(source='auto', target='en').translate(prompt_text)
    
    last_error = None
    # تجربة السيرفرات المتوفرة بالترتيب
    for space_name, api_endpoint in SPACES_TO_TRY:
        try:
            ai_client = Client(space_name, token=token)
            result = ai_client.predict(prompt=english_prompt, api_name=api_endpoint)
            return result
        except Exception as e:
            last_error = e
            continue
            
    raise last_error if last_error else Exception("جميع السيرفرات مشغول حالياً")

# 4. معالجة الرسائل
async def generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    await update.message.reply_text("⏳ جاري تحضير الفيديو وتوليده (قد يستغرق من دقيقة إلى 3 دقائق)...")
    
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(process_video_generation, user_prompt, HF_TOKEN),
            timeout=240.0
        )
        await update.message.reply_video(video=open(result, 'rb'), caption="✨ تم إنشاء الفيديو بنجاح!")
    except asyncio.TimeoutError:
        await update.message.reply_text("⚠️ استغرق السيرفر وقتاً طويلاً. أعد إرسال الطلب مجدداً.")
    except Exception as e:
        err_msg = str(e)[:200]
        await update.message.reply_text(f"❌ تعذر التوليد حالياً:\n{err_msg}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_video))
    print("Bot is running...")
    app.run_polling()
