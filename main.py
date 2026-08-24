import os
import time
import asyncio
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator

# 1. خادم ويب مصغر لإبقاء Render في حالة Live
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Active")

def run_web_port():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_port, daemon=True).start()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

# رابط السيرفر الرسمي المباشر لتوليد الفيديو (بدون مساحات شخصية)
MODEL_URL = "https://api-inference.huggingface.co/models/damo-vilab/modelscope-text-to-video-synthesis"

# 2. واجهة الترحيب /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "مرحباً بك في بوت صناعة الفيديوهات! 🎬✨\n\n"
        "أرسل لي وصف الفيديو بـ **العربية**، **الفرنسية**، أو **الإنجليزي** وسأقوم بتوليد مقطع فيديو لك!"
    )
    await update.message.reply_text(welcome_text)

# 3. طلب الفيديو مباشرة من API الرسمي
def query_official_api(prompt_text, token):
    english_prompt = GoogleTranslator(source='auto', target='en').translate(prompt_text)
    headers = {"Authorization": f"Bearer {token}"}
    
    # محاولة الإرسال مع الانتظار في حال كان السيرفر يستعد (Warm up)
    for _ in range(3):
        response = requests.post(MODEL_URL, headers=headers, json={"inputs": english_prompt}, timeout=120)
        if response.status_code == 200:
            return response.content
        elif response.status_code == 503:
            time.sleep(15) # السيرفر يحمل النموذج في الذاكرة
        else:
            break
            
    raise Exception(f"خطأ استجابة السيرفر: {response.status_code}")

# 4. معالجة الرسالة وإرسال الفيديو MP4
async def generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    status_msg = await update.message.reply_text("⏳ جاري إنشاء الفيديو عبر السيرفر الرسمي (يرجى الانتظار قليلاً)...")

    try:
        video_bytes = await asyncio.to_thread(query_official_api, user_prompt, HF_TOKEN)
        
        video_filename = "output_video.mp4"
        with open(video_filename, "wb") as f:
            f.write(video_bytes)

        with open(video_filename, "rb") as f:
            await update.message.reply_video(video=f, caption=f"🎬 **تم إنشاء الفيديو لـ:** {user_prompt}")
        
        await status_msg.delete()
    except Exception as e:
        err_msg = str(e)[:200]
        await status_msg.edit_text(f"❌ تعذر التوليد حالياً:\n{err_msg}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_video))
    print("Bot is running...")
    app.run_polling()
