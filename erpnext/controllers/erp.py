import frappe, json
from frappe.utils import cint, flt, getdate
from six import string_types

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
	from erpnext.controllers.va2 import extract_invoice_data, get_po_number, get_item_detail
	if doc.communication_type != "Communication":
		return
	
	enable = cint(frappe.get_value("Selling Settings","Selling Settings", 'enable_supplier_invoice'))
	invoice_email_default = frappe.get_value("Selling Settings","Selling Settings", 'default_email_inbox')
	if not enable or not invoice_email_default:
		return
	
	if doc.email_account != invoice_email_default:
		return
	
	result = []
	msg = doc.content

	# should check if this invoice or not

	file_doc_name = frappe.db.get_list("File", {
		"attached_to_doctype":"Communication",
		"attached_to_name":doc.name
	})
	
	# temporary detect invoice/not by attachment
	if not file_doc_name:
		return
	
	for file_name in file_doc_name:
		
		fn = frappe.get_doc('File', file_name)
		fn_name = fn.file_name
		full_path = fn.get_full_path()
		if ".pdf" in full_path:
			full_path = convert_pdf_to_img(full_path)

		temp = get_po_number(full_path)
		if temp and temp.get("result"):
			if not frappe.db.exists("Purchase Order", temp.get("result")):
				continue

			po = frappe.get_doc("Purchase Order", temp.get("result"))
			items = []
			for d in po.items:
				items.append(
					{"item_code": d.item_name, "qty":d.qty, "rate":d.rate, "uom":d.uom}
				)

			# temporary not used
			# items = get_item_detail(full_path, items)
			result.append({
				"po_no":temp.get("result"),
				"items":items
			})

	pi = []
	for res in result:
		name = create_purchase_invoice(res)
		pi.append(name)

	return pi

from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice
def create_purchase_invoice(data):
	# make PI
	doc = make_purchase_invoice(data.get("po_no"))
	doc.created_with_ai = 1
	doc.save()

	# update item
	return doc.name

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
				AND i.item_group = 'Products' and i.item_name not like "(R&D)%"
	""", as_dict=1)
	for d in items:
		if not d.item_code in context:
			keys = d.item_name
			if d.marketing_name:
				keys += "/"+d.marketing_name
			context[d.item_code] = {
				"keyword": f'{keys}'
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
			dl.link_name as customer_code,
			c.email_id,
			c.first_name,
			c.company_name,
			(SELECT 
					GROUP_CONCAT(DISTINCT ce.email_id
							ORDER BY ce.idx
							SEPARATOR ',')
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
	email_map = {}
	for d in contacts:
		other_email = (d.other_email or "").split(",")

		if not other_email and not d.email_id:
			continue
		
		if not d.name in email_map:
			email_map[d.name] = [d.email_id] + other_email
		else:
			em = [d.email_id] + other_email
			email_map[d.name] += em
	

	for d in items:
		if not d.name in context:
			emails = email_map.get(d.name) or []
			context[d.name] = {
				"keyword": d.customer_name,
				"emails":emails
			}
	
	return json.dumps(context)

def shipping_context():
	pass

def package_context():
	pass

def make_sales_order(args):
	if not args:
		return
	
	if isinstance(args, string_types):
		args = json.loads(args)

	doc = frappe.new_doc("Sales Order")
	doc.customer = args.get("company_name") #should check exist or not
	for d in args.get("items"):
		item_code = d.get("item_code")
		# temporary use default
		uom = frappe.get_value("Item", item_code, "default_packaging")
		row = doc.append("items")
		row.item_code = item_code
		row.qty = flt(d.get("qty"))
		row.uom = uom
	doc.delivery_date = getdate(args.get("delivery_date"))
	# temporary
	doc.pending_po = 1

	# temporary use default address
	addr = frappe.get_value("Customer", doc.customer, 'customer_primary_address')
	doc.customer_address = addr
	doc.shipping_address_name = addr
	doc.ai_doc = 1
	# add attachment
	doc.save()
	return doc.name
