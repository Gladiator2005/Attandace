import io
import logging
logger = logging.getLogger(__name__)

def generate_excel_report(records, title="Attendance Report"):
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = title
        ws.append(["Date", "Time", "Employee", "Entry Type", "Confidence", "Status"])
        for r in records:
            ws.append([str(getattr(r, 'timestamp', '')), getattr(r, 'entry_type', ''), "", "", str(getattr(r, 'confidence_score', '')), "Verified" if getattr(r, 'is_verified', False) else "Unverified"])
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Excel generation error: {e}")
        return None

def generate_pdf_report(records, title="Attendance Report"):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        output = io.BytesIO()
        c = canvas.Canvas(output, pagesize=A4)
        c.drawString(50, 800, title)
        y = 760
        for r in records:
            c.drawString(50, y, f"{getattr(r, 'timestamp', '')} - {getattr(r, 'entry_type', '')}")
            y -= 20
            if y < 50:
                c.showPage()
                y = 800
        c.save()
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        return None
