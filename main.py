import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from gradio_client import Client
from deep_translator import GoogleTranslator

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

async def generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    await update.message.reply_text("⏳ جاري فهم الوصف وإنشاء الفيديو، يرجى الانتظار...")
    
    try:
        # ترجمة النص تلقائياً للإنجليزية ليفهمه نموذج الفيديو
        english_prompt = GoogleTranslator(source='auto', target='en').translate(user_prompt)
        
        # الاتصال بالنموذج وتوليد الفيديو
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
