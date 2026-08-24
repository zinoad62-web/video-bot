import os
import requests
from urllib.parse import quote
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator

# ضع التوكن الخاص ببوتك هنا
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك! أرسل لي أي وصف باللغة العربية وسأقوم بتوليد تصميم عالي الجودة لك 🎨")

async def generate_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    status_msg = await update.message.reply_text("⏳ جاري تحضير الطلب وتوليد التصميم...")

    try:
        # 1. ترجمة الوصف إلى الإنجليزية للحصول على أفضل نتيجة
        translated_prompt = GoogleTranslator(source='auto', target='en').translate(user_prompt)
        encoded_prompt = quote(translated_prompt)

        # 2. إنشاء رابط التوليد المباشر (Flux Engine)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true"

        # 3. تحميل الصورة/المقطع وتأكيد الاستجابة
        response = requests.get(image_url, timeout=30)
        
        if response.status_code == 200:
            await update.message.reply_photo(
                photo=response.content,
                caption=f"✨ **النتيجة لـ:** {user_prompt}"
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ تعذر توليد التصميم حالياً، يرجى المحاولة لاحقاً.")

    except Exception as e:
        print(f"Error: {e}")
        await status_msg.edit_text("❌ حدث خطأ أثناء معالجة الطلب. يرجى إعادة المحاولة.")

if __name__ == "__main__":
    # تثبيت التبعيات المطلوبة قبل التشغيل:
    # pip install python-telegram-bot requests deep-translator

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_media))
    
    print("البوت يعمل الآن...")
    app.run_polling()
