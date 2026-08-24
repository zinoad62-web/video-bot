import os
import io
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# 1. خادم وهمي لإبقاء Render في حالة Live
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Doc Generator Active")

def run_web_port():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_port, daemon=True).start()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# 2. رسالة الترحيب والتعليمات عند /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "مرحباً بك في بوت صانع المستندات والوثائق التعليمية! 📄🎓\n\n"
        "يمكنني توليد مستندات رسمية قابلة للطباعة والتعديل بصيغة (Word) مثل:\n"
        "• 📝 **أوراق إجابة واستمارات اختبارات**\n"
        "• 📜 **تصاريح شرفية وشهادات حضور/تقدير**\n"
        "• ✉️ **استدعاءات ومراسلات إدارية للمؤسسات**\n\n"
        "أرسل لي وصف المستند وما تريد تضمينه فيه (بالعربية، الفرنسية، أو الإنجليزية) وسأصممه لك فوراً!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# 3. بناء وتنسيق المستند التعليمي
def create_educational_document(prompt_text: str) -> io.BytesIO:
    doc = Document()
    
    # ضبط الهوامش
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # الهيدر العلوي للمؤسسة التعليمية
    header_table = doc.add_table(rows=1, cols=2)
    header_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    header_table.autofit = False
    
    cell_left = header_table.rows[0].cells[0]
    cell_right = header_table.rows[0].cells[1]
    
    p_right = cell_right.paragraphs[0]
    p_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_r = p_right.add_run("المملكة / الدولة: ....................\nالمؤسسة التعليمية: ....................\nالموسم الدراسي: 2025 / 2026")
    run_r.font.size = Pt(10)
    run_r.font.name = "Arial"

    p_left = cell_left.paragraphs[0]
    p_left.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run_l = p_left.add_run("République / Institution\nAnnée Scolaire: 2025/2026\nClass / القسم: ....................")
    run_l.font.size = Pt(10)
    run_l.font.name = "Arial"

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # عنوان المستند الرئيسي
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # تحديد العنوان حسب الكلمات المفتاحية
    if "إجابة" in prompt_text or "اختبار" in prompt_text or "answer" in prompt_text:
        title_text = "ورقة إجابة رسمية - EXAM ANSWER SHEET"
    elif "تصريح" in prompt_text or "شهادة" in prompt_text or "statement" in prompt_text:
        title_text = "تصريح إداري / شهادة رسمية"
    else:
        title_text = "مستند تعليمي إداري"

    title_run = title_p.add_run(title_text)
    title_run.font.bold = True
    title_run.font.size = Pt(18)
    title_run.font.color.rgb = RGBColor(0, 51, 102)
    title_p.paragraph_format.space_after = Pt(18)

    # جدول بيانات الطالب / المستفيد
    info_table = doc.add_table(rows=2, cols=2)
    info_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    info_table.style = 'Table Grid'
    
    info_table.rows[0].cells[1].paragraphs[0].text = "الاسم واللقب: ..........................................."
    info_table.rows[0].cells[0].paragraphs[0].text = "Nom & Prénom: ......................................."
    info_table.rows[1].cells[1].paragraphs[0].text = "المادة / الموضوع: ....................................."
    info_table.rows[1].cells[0].paragraphs[0].text = "تاريخ التقديم: ..... / ..... / 2026"
    
    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # محتوى الطلب المدخل من المستخدم
    body_header = doc.add_paragraph()
    bh_run = body_header.add_run("تفاصيل المستند / Content Details:")
    bh_run.font.bold = True
    bh_run.font.size = Pt(12)

    body_p = doc.add_paragraph()
    body_run = body_p.add_run(prompt_text)
    body_run.font.size = Pt(11)
    body_p.paragraph_format.space_after = Pt(20)

    # قسم خاص بالأسئلة أو جدول الإجابات إذا كان المطلوب ورقة إجابة
    if "إجابة" in prompt_text or "اختبار" in prompt_text or "answer" in prompt_text:
        q_table = doc.add_table(rows=6, cols=3)
        q_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        q_table.style = 'Table Grid'
        
        headers = ["رقم السؤال / Q#", "إجابة الطالب / Answer", "العلامة / Mark"]
        for i, h in enumerate(headers):
            cell = q_table.rows[0].cells[i]
            cell.paragraphs[0].text = h
            cell.paragraphs[0].runs[0].font.bold = True
            
        for row_idx in range(1, 6):
            q_table.rows[row_idx].cells[0].paragraphs[0].text = f"السؤال {row_idx}"

    doc.add_paragraph().paragraph_format.space_after = Pt(30)

    # قسم التوقيع والختم الإداري
    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_table.rows[0].cells[1].paragraphs[0].text = "توقيع وختم الإدارة / الأستاذ:\n\n.........................................."
    sig_table.rows[0].cells[0].paragraphs[0].text = "توقيع الطالب / المعني:\n\n.........................................."

    # حفظ المستند في الذاكرة
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream

# 4. استقبال الرسائل وتوليد الوثيقة
async def handle_document_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    status_msg = await update.message.reply_text("⏳ جاري تصميم وتنسيق المستند التعليمي...")

    try:
        # إنشاء ملف Word
        doc_stream = create_educational_document(user_prompt)
        
        # إرسال المستند جاهزاً للتحميل
        await update.message.reply_document(
            document=doc_stream,
            filename="Educational_Document.docx",
            caption="✅ تم إنشاء المستند بنجاح! يمكنك فتحه وتعديله أو طباعته مباشرة."
        )
        await status_msg.delete()

    except Exception as e:
        err_msg = str(e)[:200]
        await status_msg.edit_text(f"❌ حدث خطأ أثناء إنشاء المستند:\n{err_msg}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_document_request))
    print("Document Bot is running...")
    app.run_polling()
