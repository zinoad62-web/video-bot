import os
import io
import json
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# 1. خادم ويب مصغر لإبقاء Render في حالة Live
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Doc AI Generator Active")

def run_web_port():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_port, daemon=True).start()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 2. رسالة الترحيب /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "مرحباً بك في صانع المستندات الذكي! 📄🤖\n\n"
        "اكتب لي أي وصف لمستند تعليمي أو إداري (مثل: قائمة نقاط، شهادة، استدعاء، جدول تنقيط...) "
        "مع ذكر التفاصيل والأعمدة وعدد الصفوف، وسأقوم بتحليل الطلب بالذكاء الاصطناعي وإنشاء المستند بدقة عالية!"
    )
    await update.message.reply_text(welcome_text)

# 3. دالة تحليل الطلب واستخراج الهيكل بالذكاء الاصطناعي
def generate_doc_structure_from_ai(user_prompt: str) -> dict:
    if not GEMINI_API_KEY:
        raise Exception("لم يتم إضافة GEMINI_API_KEY في إعدادات Render!")

    model = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt_instruction = f"""
    أنت خبير في إنشاء وتصميم المستندات والوثائق المدرسية والإدارية.
    قم بتحليل طلب المستخدم بدقة واغرس كافة الأعمدة والبيانات والصفوف المطلوبة، ثم أرجع النتيجة على شكل JSON فقط بدون أي كلام خارجي:

    {{
        "header_top": "النص الهيدر العلوي الكامل مثلاً (الجمهورية الجزائرية الديمقراطية الشعبية / وزارة التربية الوطنية)",
        "title": "العنوان الرئيسي المكتوب في الأعلى",
        "metadata": ["المادة: الرياضيات", "السنة: الأولى متوسط", "الأستاذ: ...", "السنة الدراسية: 2025/2026"],
        "has_table": true,
        "table_columns": ["الرقم", "اللقب", "الاسم", "القسم", "المراقبة المستمرة", "الفرض", "الاختبار", "المعدل", "الملاحظة"],
        "rows_count": 35,
        "footer_notes": "توقيع الأستاذ / ختم الإدارة"
    }}

    طلب المستخدم:
    {user_prompt}
    """

    response = model.generate_content(prompt_instruction)
    text = response.text.strip()
    
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
        
    return json.loads(text.strip())

# 4. تحويل هيكل JSON إلى مستند Word محترف
def build_docx_from_structure(doc_data: dict) -> io.BytesIO:
    doc = Document()
    
    # ضبط الهوامش
    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    # الهيدر العلوي
    header_text = doc_data.get("header_top", "")
    if header_text:
        p_head = doc.add_paragraph()
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_head = p_head.add_run(header_text)
        r_head.font.bold = True
        r_head.font.size = Pt(11)
        p_head.paragraph_format.space_after = Pt(6)

    # العنوان الرئيسي
    title_text = doc_data.get("title", "مستند رسمي")
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run(title_text)
    r_title.font.bold = True
    r_title.font.size = Pt(15)
    r_title.font.color.rgb = RGBColor(0, 51, 102)
    p_title.paragraph_format.space_after = Pt(10)

    # البيانات الإضافية (الأستاذ، السنة، المادة...)
    metadata = doc_data.get("metadata", [])
    if metadata:
        p_meta = doc.add_paragraph()
        p_meta.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_meta = p_meta.add_run("  |  ".join(metadata))
        r_meta.font.size = Pt(10)
        r_meta.font.bold = True
        p_meta.paragraph_format.space_after = Pt(12)

    # إنشاء الجدول الديناميكي بناءً على الأعمدة وعدد الصفوف
    if doc_data.get("has_table", False):
        cols = doc_data.get("table_columns", ["الرقم", "الاسم واللقب"])
        rows_cnt = doc_data.get("rows_count", 10)
        
        table = doc.add_table(rows=rows_cnt + 1, cols=len(cols))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = 'Table Grid'
        
        # رأس الجدول
        hdr_cells = table.rows[0].cells
        for idx, col_name in enumerate(cols):
            hdr_cells[idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = hdr_cells[idx].paragraphs[0].add_run(col_name)
            r.font.bold = True
            r.font.size = Pt(9.5)
            
        # صفوف الترقيم والبيانات
        for r_idx in range(1, rows_cnt + 1):
            row_cells = table.rows[r_idx].cells
            for c_idx in range(len(cols)):
                row_cells[c_idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                # ترقيم تلقائي لعمود الرقم
                if c_idx == 0 and ("رقم" in cols[0] or "الرقم" in cols[0] or "N°" in cols[0]):
                    row_cells[0].paragraphs[0].text = str(r_idx)

    # التوقيع والملاحظات
    footer_notes = doc_data.get("footer_notes", "")
    if footer_notes:
        doc.add_paragraph().paragraph_format.space_before = Pt(15)
        p_foot = doc.add_paragraph()
        p_foot.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r_foot = p_foot.add_run(footer_notes)
        r_foot.font.size = Pt(10)
        r_foot.font.bold = True

    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream

# 5. معالجة الرسائل
async def handle_document_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    status_msg = await update.message.reply_text("🧠 جاري تحليل وصفك بالذكاء الاصطناعي وبناء كافة الصفوف والأعمدة المطلوب...")

    try:
        # استخراج الهيكل بالذكاء الاصطناعي
        doc_data = await asyncio.to_thread(generate_doc_structure_from_ai, user_prompt)
        
        # بناء ملف docx
        doc_stream = await asyncio.to_thread(build_docx_from_structure, doc_data)
        
        await update.message.reply_document(
            document=doc_stream,
            filename="Document_Custom.docx",
            caption="✨ **تم إنشاء المستند بالذكاء الاصطناعي بناءً على وصفك الدقيق!**"
        )
        await status_msg.delete()

    except Exception as e:
        err_msg = str(e)[:250]
        await status_msg.edit_text(f"❌ حدث خطأ:\n{err_msg}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_document_request))
    print("AI Document Bot is running...")
    app.run_polling()
