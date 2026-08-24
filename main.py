import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from gradio_client import Client
from deep_translator import GoogleTranslator

# 1. فتح منفذ خفيف لإبقاء سيرفر Render شغالاً (Live)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Video Bot is Active")

def run_web_port():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_port, daemon=True).start()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

# 2. واجهة الترحيب عند فتح البوت /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "مرحباً بك في بوت صناعة الفيديوهات! 🎬✨\n\n"
        "أرسل لي وصف الفيديو الذي تريد إنشاءه بأي لغة:\n"
        "• العربية 🇸🇦\n"
        "• الفرنسية 🇫🇷\n"
        "• الإنجليزية 🇬🇧\n\n"
        "وسأقوم بتوليد فيديو متحرك لك!"
    )
    await update.message.reply_text(welcome_text)

# 3. دالة توليد الفيديو الحقيقي عبر HuggingFace
def generate_video_file(prompt_text, token):
    # ترجمة النص للإنجليزية لضمان أفضل جودة
    english_prompt = GoogleTranslator(source='auto', target='en').translate(prompt_text)
    
    # قائمة بمساحات سيرفرات الفيديو المتاحة
    spaces_to_try = [
        "fffiloni/LTX-Video-playground",
        "ZeroGPU-explorers/LTX-Video",
        "hao-nguyen/LTX-Video"
    ]
    
    last_err = None
    for space in spaces_to_try:
        try:
            client = Client(space, token=token)
            result = client.predict(
                prompt=english_prompt,
                api_name="/predict"
            )
            if isinstance(result, (list, tuple)):
                return result[0]
            return result
        except Exception as e:
            last_err = e
            continue
            
    raise last_err if last_err else Exception("جميع سيرفرات الفيديو متوقفة حالياً")

# 4. استقبال الرسائل وإرسال الفيديو MP4
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    status_msg = await update.message.reply_text("⏳ جاري ترجمة الوصف وإنشاء الفيديو (MP4)...\nيرجى الانتظار من 2 إلى 4 دقائق حسب طابور السيرفر 🎬")

    try:
        # تشغيل التوليد في الخلفية بمهلة 5 دقائق
        video_path = await asyncio.wait_for(
            asyncio.to_thread(generate_video_file, user_prompt, HF_TOKEN),
            timeout=300.0
        )

        # إرسال الفيديو المكتمل للمستخدم
        with open(video_path, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file,
                caption=f"🎬 **تم إنشاء الفيديو لـ:** {user_prompt}"
            )
        await status_msg.delete()

    except asyncio.TimeoutError:
        await status_msg.edit_text("⚠️ استغرق السيرفر وقتاً طويلاً في طابور الانتظار. أرسل الطلب مرة أخرى.")
    except Exception as e:
        err_details = str(e)[:200]
        await status_msg.edit_text(f"❌ تعذر إنشاء الفيديو حالياً:\n{err_details}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running...")
    app.run_polling()
