import os
import io
import json
import urllib.request
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# خادم حيوية لإبقاء البوت متصلاً
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_web_port():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_port, daemon=True).start()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def call_gemini_direct(prompt: str) -> dict:
    if not GEMINI_API_KEY:
        raise Exception("مفتاح GEMINI_API_KEY غير موجود في إعدادات Render!")

    # 1. اكتشاف النماذج المتاحة لمفتاحك تلقائياً لتفادي خطأ 404 نهائياً
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    req_list = urllib.request.Request(list_url)
    
    try:
        with urllib.request.urlopen(req_list, timeout=15) as res:
            models_data = json.loads(res.read().decode('utf-8'))
            
        valid_models = []
        for m in models_data.get("models", []):
            methods = m.get("supportedGenerationMethods", [])
            if "generateContent" in methods:
                valid_models.append(m['name']) # مثال: models/gemini-1.5-flash
    except Exception as e:
        raise Exception(f"خطأ في مفتاح Google API: {e}")

    if not valid_models:
        raise Exception("لم يتم العثور على أي نموذج مفعل لهذا المفتاح.")

    system_instruction = (
        "أنت خبير في تصميم الوثائق المدرسية والإدارية. قم بتحليل طلب المستخدم وأرجع الناتج بصيغة JSON فقط "
        "بدون أي كلام خارجي أو تنسيق markdown:\n"
        "{\n"
        '  "header_top": "الجمهورية الجزائرية الديمقراطية الشعبية",\n'
        '  "title": "قائمة نتائج الرياضيات - السنة الأولى متوسط",\n'
        '  "metadata": ["المادة: الرياضيات", "السنة: الأولى متوسط", "الأستاذ: ...", "السنة الدراسية: 2025/2026"],\n'
        '  "has_table": true,\n'
        '  "table_columns": ["الرقم", "اللقب", "الاسم", "القسم", "المراقبة المستمرة", "الفرض", "الاختبار", "المعدل", "الملاحظة"],\n'
        '  "rows_count": 35,\n'
        '  "footer_notes": "توقيع الأستاذ / ختم الإدارة"\n'
        "}"
    )

    payload = {
        "contents": [{
            "parts": [{"text": f"{system_instruction}\n\nطلب المستخدم:\n{prompt}"}]
        }]
    }
    data = json.dumps(payload).encode('utf-8')

    # 2. تجربة النماذج المكتشفة بالترتيب
    last_err = None
    for model_full_name in valid_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_full_name}:generateContent?key={GEMINI_API_KEY}"
        try:
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as response:
                res_body = response.read().decode('utf-8')
                res_json = json.loads(res_body)
                text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
                
                if text.startswith("```json"): text = text[7:]
                if text.startswith("```"): text = text[3:]
                if text.endswith("```"): text = text[:-3]
                return json.loads(text.strip())
        except Exception as e:
            last_err = e
            continue

    raise Exception(f"تعذر التوليد: {last_err}")

def build_docx(doc_data: dict) -> io.BytesIO:
    doc = Document()
    for s in doc.sections:
        s.top_margin = Inches(0.5)
        s.bottom_margin = Inches(0.5)
        s.left_margin = Inches(0.5)
        s.right_margin = Inches(0.5)

    if doc_data.get("header_top"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(doc_data["header_top"])
        r.font.bold = True
        r.font.size = Pt(11)

    if doc_data.get("title"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(doc_data["title"])
        r.font.bold = True
        r.font.size = Pt(14)
        r.font.color.rgb = RGBColor(0, 51, 102)

    if doc_data.get("metadata"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = p.add_run("  |  ".join(doc_data["metadata"]))
        r.font.bold = True
        r.font.size = Pt(10)

    if doc_data.get("has_table", False):
        cols = doc_data.get("table_columns", ["الرقم", "الاسم"])
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

    if doc_data.get("footer_notes"):
        doc.add_paragraph()
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(doc_data["footer_notes"])
        r.font.bold = True

    stream = io.BytesIO()
    doc.save(stream)
    stream.seek(0)
    return stream

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً بك! أرسل لي وصف المستند وسأقوم بإنشائه فوراً.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = await update.message.reply_text("⏳ جاري التعرف على نموذج الذكاء الاصطناعي وبناء المستند...")
    try:
        data = await asyncio.to_thread(call_gemini_direct, update.message.text)
        doc_bytes = await asyncio.to_thread(build_docx, data)
        await update.message.reply_document(document=doc_bytes, filename="Document.docx", caption="✨ تم إنشاء المستند بنجاح!")
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ خطأ: {str(e)[:250]}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
