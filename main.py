import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from gradio_client import Client

# جلب المفاتيح من متغيرات البيئة في Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

ai_client = Client("Lightricks/LTX-Video", hf_token=HF_TOKEN)

async def generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    await update.message.reply_text("⏳ جاري إنشاء الفيديو، قد يستغرق الأمر دقيقة...")
    
    try:
        result = ai_client.predict(prompt=user_prompt, api_name="/predict")
        await update.message.reply_video(video=open(result, 'rb'))
    except Exception:
        await update.message.reply_text("السيرفر مشغول حالياً، يرجى المحاولة بعد قليل.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_video))
    app.run_polling()
