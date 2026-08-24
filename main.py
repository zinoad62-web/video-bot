import os
import io
import json
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# خادم حيوية لإبقاء المنصة تعمل
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Active")

def run_web_port():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_port, daemon=True).start()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً بك! اكتب لي وصف المستند المطلوب وسأقوم بإنشائه فوراً.")

def generate_doc_structure_from_ai(user_prompt: str) -> dict:
    if not GEMINI_API_KEY:
        raise Exception("لم يتم ضبط GEMINI_API_KEY في Render!")

    # استخدام الحزمة الرسمية الجديدة
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt_instruction = f"""
    أنت خبير في إنشاء وتصميم المستندات المدرسية والإدارية.
    قم بتحليل طلب المستخدم واستخرج البيانات، وأرجع النتيجة بصيغة JSON فقط بدون أي نص إضافي:
    {{
        "header_top": "الجمهورية الجزائرية الديمقراطية الشعبية",
        "title": "قائمة نتائج الرياضيات - السنة الأولى متوسط",
        "metadata": ["المادة: الرياضيات", "السنة: الأولى متوسط", "الأستاذ: ...", "السنة الدراسية: 2025/2026"],
        "has_table": true,
        "table_columns": ["الرقم", "اللقب", "الاسم", "القسم", "المراقبة المستمرة", "الفرض", "الاختبار", "المعدل", "الملاحظة"],
        "rows_count": 35,
        "footer_notes": "توقيع الأستاذ / ختم الإدارة"
    }}

    طلب المستخدم:
    {user_prompt}
    """

    # تجربة النماذج الحديثة المعتمدة
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    last_err = None

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_instruction
            )
            text = response.text.strip()
            if text.startswith("```json"): text = text[7:]
            if text.startswith("```"): text = text[3:]
            if text.endswith("```"): text = text[:-3]
            return json.loads(text.strip())
        except Exception as e:
            last_err = e
            continue

    raise last_err if last_err else Exception("تعذر الاتصال بجميع النماذج")

def build_docx_from_structure(doc_data: dict) -> io.BytesIO:
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    header_text = doc_data.get("header_top", "")
    if header_text:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(header_text)
        r.font.bold = True
        r.font.size = Pt(11)

    title_text = doc_data.get("title", "مستند رسمي")
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run(title_text)
    r_title.font.bold = True
    r_title.font.size = Pt(14)
    r_title.font.color.rgb = RGBColor(0, 51, 102)

    metadata = doc_data.get("metadata", [])
    if metadata:
        p_meta = doc.add_paragraph()
        p_meta.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_meta = p_meta.add_run("  |  ".join(metadata))
        r_meta.font.size = Pt(10)
        r_meta.font.bold = True

    if doc_data.get("has_table", False):
        cols = doc_data.get("table_columns", ["الرقم", "الاسم واللقب"])
        rows_cnt = doc_data.get("rows_count", 10)
        
        table = doc.add_table(rows=rows_cnt + 1, cols=len(cols))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = 'Table Grid'
        
        hdr_cells = table.rows[0].cells
        for idx, col_name in enumerate(cols):
            hdr_cells[idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = hdr_cells[idx].paragraphs[0].add_run(col_name)
            r.font.bold = True
            r.font.size = Pt(9.5)
            
        for r_idx in range(1, rows_cnt + 1):
            row_cells = table.rows[r_idx].cells
            for c_idx in range(len(cols)):
                row_cells[c_idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                if c_idx == 0:
                    row_cells[0].paragraphs[0].text = str(r_idx)

    footer = doc_data.get("footer_notes", "")
    if footer:
        doc.add_paragraph()
        p_f = doc.add_paragraph()
        p_f.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r_f = p_f.add_run(footer)
        r_f.font.bold = True

    stream = io.BytesIO()
    doc.save(stream)
    stream.seek(0)
    return stream

async def handle_document_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⏳ جاري تحليل الطلب وإنشاء جدول 35 تلميذاً...")
    try:
        doc_data = await asyncio.to_thread(generate_doc_structure_from_ai, update.message.text)
        doc_stream = await asyncio.to_thread(build_docx_from_structure, doc_data)
        await update.message.reply_document(document=doc_stream, filename="Document.docx", caption="✨ تم التوليد بنجاح!")
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ خطأ: {str(e)[:200]}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_document_request))
    app.run_polling()
