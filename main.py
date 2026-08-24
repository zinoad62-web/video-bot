import os
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from gradio_client import Client
from deep_translator import GoogleTranslator

# إنشاء موقع وهمي لإبقاء Render سعيداً
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is alive!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# تشغيل خادم الويب في الخلفية
Thread(target=run_web_server).start()

# جلب المفاتيح من متغيرات البيئة
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

async def generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    await update.message.reply_text("⏳ جاري فهم الوصف وإنشاء الفيديو، يرجى الانتظار...")
    
    try:
        # ترجمة النص للإنجليزية تلقائياً
        english_prompt = GoogleTranslator(source='auto', target='en').translate(user_prompt)
        
        # توليد الفيديو
        ai_client = Client("Lightricks/LTX-Video", token=HF_TOKEN)
        result = ai_client.predict(prompt=english_prompt, api_name="/predict")
        await update.message.reply_video(video=open(result, 'rb'))
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("حدث خطأ في السيرفر أو أن الطابور ممتلئ، حاول مجدداً بعد قليل.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_video))
    print("Bot is running...")
    app.run_polling()
