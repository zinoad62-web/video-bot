import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from gradio_client import Client
from deep_translator import GoogleTranslator

# سيرفر بسيط لضمان استمرار عمل البوت على منصات الاستضافة مثل Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running!")

def run_web_port():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_port, daemon=True).start()

# جلب التوكنات من متغيرات البيئة
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

# أمر الترحيب عند بدء استخدام البوت (/start)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **أهلاً بك في بوت صانع الفيديوهات الذكي!**\n\n"
        "يمكنني تحويل أي فكرة أو وصف إلى فيديو مميز خلال لحظات باستخدام الذكاء الاصطناعي.\n\n"
        "🌐 **اللغات المدعومة:**\n"
        "يمكنك كتابة الوصف بأي لغة تريدها:\n"
        "• 🇸🇦 **العربية** (مثال: قط يحمل مظلة تحت المطر)\n"
        "• 🇫🇷 **الفرنسية** (مثال: Un chat avec un parapluie sous la pluie)\n"
        "• 🇬🇧 **الإنجليزيّة** (مثال: A cat holding an umbrella in the rain)\n\n"
        "✨ **أرسل وصف الفيديو الآن وسأقوم بإنشائه لك فوراً!**"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# معالجة طلبات إنشاء الفيديو
async def generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text.strip()
    
    # إرسال رسالة انتظار للمستخدم
    status_msg = await update.message.reply_text(
        "⏳ **جاري ترجمة الوصف وإنشاء الفيديو...**\nيرجى الانتظار بضع ثوانٍ 🎬",
        parse_mode="Markdown"
    )
    
    try:
        # ترجمة النص تلقائياً إلى اللغة الإنجليزية لضمان أفضل نتيجة للنموذج
        english_prompt = GoogleTranslator(source='auto', target='en').translate(user_prompt)
        
        # الاتصال بنموذج توليد الفيديو
        ai_client = Client("Lightricks/ltx-video-distilled", token=HF_TOKEN)
        
        # استدعاء واجهة إنشاء الفيديو
        result = ai_client.predict(
            prompt=english_prompt,
            negative_prompt="worst quality, low quality, blurry, distorted motion",
            api_name="/generate_video"
        )
        
        # رفع وإرسال الفيديو للمستخدم
        await status_msg.edit_text("📤 **تم إنشاء الفيديو بنجاح! جاري الرفع...**", parse_mode="Markdown")
        await update.message.reply_video(
            video=open(result, 'rb'),
            caption=f"🎬 **الوصف:** {user_prompt}\n🔤 **الترجمة للنموذج:** {english_prompt}"
        )
    except Exception as e:
        error_details = str(e)[:200]
        await status_msg.edit_text(
            f"❌ **حدث خطأ أثناء إنشاء الفيديو:**\n`{error_details}`\n\nيرجى إعادة المحاولة بعد القليل.",
            parse_mode="Markdown"
        )

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        print("⚠️ خطأ: لم يتم ضبط TELEGRAM_TOKEN في متغيرات البيئة.")
    else:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # إضافات المعالجة
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_video))
        
        print("✅ البوت جاهز ويعمل الآن...")
        app.run_polling()
