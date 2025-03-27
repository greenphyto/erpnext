import frappe, json
from frappe.utils import cint

def check_email_status(log, method=""):
    if log.status != "Sent":
        return
    
    comm_name = frappe.get_value("Communication", {"message_id":log.message_id})
    if not comm_name:
        return
    
    doc = frappe.get_doc("Communication", comm_name)
    if not doc.reference_doctype and doc.reference_name:
        return
    
    if doc.reference_doctype in ["Purchase Order"]:
        frappe.db.set_value(doc.reference_doctype, doc.reference_name, "email_status", "Y")

    notif = frappe.get_doc("Notification", "Email Sent Status")
    notif.send(doc)

def read_email_inbox(doc, method=""):
    from erpnext.controllers.va2 import extract_invoice_data
    if doc.communication_type != "Communication":
        return
    
    enable = cint(frappe.get_value("Selling Settings","Selling Settings", 'enable_supplier_invoice'))
    invoice_email_default = frappe.get_value("Selling Settings","Selling Settings", 'default_email_inbox')
    if not enable or not invoice_email_default:
        return
    
    if doc.email_account != invoice_email_default:
        return
    
    msg = doc.content
    file_doc_name = frappe.db.get_list("File", {
        "attached_to_doctype":"Communication",
        "attached_to_name":doc.name
    })
    for file_name in file_doc_name:
        
        fn = frappe.get_doc('File', file_name)
        full_path = fn.get_full_path()
        if ".pdf" in full_path:
            full_path = convert_pdf_to_img(full_path)

        res = extract_invoice_data(full_path)

def convert_pdf_to_img(path):
    import fitz  # PyMuPDF
    import numpy as np
    from PIL import Image

    doc = fitz.open(path)

    page = doc[0]

    pix = page.get_pixmap()

    image_np = np.array(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))

    return image_np

def get_item_context():
	# build item list as base knowledge / context for AI
	context = {}
	# we limit to products and enable
	items = frappe.db.sql("""
		SELECT 
			i.name AS item_code, i.item_name, i.marketing_name
		FROM
			`tabItem` i
		WHERE
			i.disabled = 0
				AND i.item_group = 'Products'
	""", as_dict=1)
	for d in items:
		if not d.item_code in context:
			context[d.item_code] = {
				"keyword": f'{d.item_name}/{d.marketing_name or ""}'
			}
	
	return json.dumps(context)

def get_customer_context():
	context = {}
	items = frappe.db.sql("""
		SELECT 
			c.name, c.customer_name
		FROM
			`tabCustomer` c
		WHERE
			c.disabled = 0 AND c.is_frozen = 0
	""", as_dict=1)

	contacts = frappe.db.sql("""
		SELECT 
			dl.link_name,
			c.email_id,
			c.first_name,
			c.company_name,
			(SELECT 
					GROUP_CONCAT(DISTINCT ce.email_id
							ORDER BY ce.idx
							SEPARATOR ', ')
				FROM
					`tabContact Email` ce
				WHERE
					ce.parent = c.name AND ce.is_primary = 0) AS other_email
		FROM
			`tabDynamic Link` dl
				LEFT JOIN
			`tabContact` c ON c.name = dl.parent
		WHERE
			dl.link_doctype = 'Customer'
	""", as_dict=1)

	# not yet
	# join contacts to customer

	for d in items:
		if not d.name in context:
			context[d.item_code] = {
				"keyword": d.name
			}
	
	return json.dumps(context)