import io
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

def add_page_numbers(pdf_bytes: bytes,
                     font="Helvetica",
                     font_size=9,
                     margin_bottom=10,
                     text_tpl="Page {i} of {n}") -> bytes:
    """
    Tambahkan nomor halaman di bottom-center PDF.
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    total = len(reader.pages)

    for i, page in enumerate(reader.pages, start=1):
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)

        # Buat overlay
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(w, h))
        text = text_tpl.format(i=i, n=total)

        c.setFont(font, font_size)
        text_width = c.stringWidth(text, font, font_size)

        # posisi: tengah bawah
        x = (w - text_width) / 2
        y = margin_bottom
        c.drawString(x, y, text)
        c.save()
        packet.seek(0)

        overlay = PdfReader(packet).pages[0]
        page.merge_page(overlay)
        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


import frappe
from frappe.utils.pdf import get_pdf

@frappe.whitelist()
def download_pdf_with_pagenum(doctype, name, format=None, doc=None, no_letterhead=0):
    html = frappe.get_print(
        doctype,
        name,
        print_format=format,
        doc=doc,
        no_letterhead=no_letterhead
    )
    raw_pdf = get_pdf(html)
    stamped_pdf = add_page_numbers(raw_pdf)

    frappe.local.response.filename = f"{name}.pdf"
    frappe.local.response.filecontent = stamped_pdf
    frappe.local.response.type = "pdf"
