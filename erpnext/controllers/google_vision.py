import frappe
import io
from google.cloud import vision
from google.api_core.client_options import ClientOptions

def extarct_text_from_file(file_path):
    if file_path.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    else:
        return extract_text_from_image(file_path)

def extract_text_from_image(image_path):
    token_key = frappe.local.conf.get("google_cloud_vision_key")
    if not token_key:
        frappe.throw("Please set the Google Vision API Key in the configuration")

    client_options = ClientOptions(api_key=token_key)
    client = vision.ImageAnnotatorClient(client_options=client_options)

    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)

    response = client.document_text_detection(image=image)
    annotation = response.full_text_annotation

    text = annotation.text or ""

    if response.error.message:
        raise Exception(f"Failed to process API: {response.error.message}")

    return text.strip()

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using Google Vision API by splitting pages into images.
    
    Uses PyMuPDF (fitz) to render pages — no poppler required.
    Uses DOCUMENT_TEXT_DETECTION for better OCR accuracy on documents.
    """
    try:
        import fitz
    except ImportError:
        frappe.throw("Please install PyMuPDF: pip install pymupdf")

    token_key = frappe.local.conf.get("google_cloud_vision_key")
    if not token_key:
        frappe.throw("Please set the Google Vision API Key in the configuration")

    client_options = ClientOptions(api_key=token_key)
    client = vision.ImageAnnotatorClient(client_options=client_options)

    all_text = ""
    doc = fitz.open(pdf_path)

    if doc.needs_pass:
        raise Exception("Encrypted PDF")

    for i, page in enumerate(doc):
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")

        image = vision.Image(content=img_bytes)
        response = client.document_text_detection(image=image)
        annotation = response.full_text_annotation

        if annotation and annotation.text:
            all_text += annotation.text + "\n"

        if response.error.message:
            raise Exception(f"Failed on page {i+1}: {response.error.message}")

    doc.close()
    return all_text.strip()