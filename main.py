import os
import requests
import threading
from urllib.parse import quote
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator

# 1. فتح منفذ الويب لإرضاء Render ومنع إيقاف السيرفر
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

# 2. قراءة التوكن من متغيرات بيئة Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# 3. رسالة الترحيب /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "مرحباً بك! 🎬✨\n\n"
        "أنا بوت الذكاء الاصطناعي لتوليد التصاميم والفيديوهات.\n"
        "أرسل لي الوصف بأي لغة (عربي، فرنسي، أو إنجليزي) وسأقوم بتوليده لك فوراً!"
    )
    await update.message.reply_text(welcome_text)

# 4. معالجة الطلبات والتوليد الفوري
async def generate_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    status_msg = await update.message.reply_text("⏳ جاري فهم الوصف وتوليد التصميم...")

    try:
        # ترجمة النص إلى الإنجليزية لضمان أفضل نتيجة
        translated_prompt = GoogleTranslator(source='auto', target='en').translate(user_prompt)
        encoded_prompt = quote(translated_prompt)
        
        # رابط محرك التوليد الفوري
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true"

        response = requests.get(image_url, timeout=30)
        
        if response.status_code == 200:
            await update.message.reply_photo(
                photo=response.content,
                caption=f"✨ **النتيجة لـ:** {user_prompt}"
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ تعذر إنشاء التصميم حالياً، حاول مجدداً.")
    except Exception as e:
        print(f"Error: {e}")
        await status_msg.edit_text("❌ حدث خطأ أثناء التوليد، يرجى إعادة المحاولة.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_media))
    
    print("Bot is running...")
    app.run_polling()
