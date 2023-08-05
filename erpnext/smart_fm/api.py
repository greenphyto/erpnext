import frappe

@frappe.whitelist(allow_guest=0)
def qrcode():
	form_dict = frappe.local.form_dict
	
	if form_dict:
		return get_qrcode_data(form_dict.get("qr"))
	return 

def get_qrcode_data(code):
	"""
		GET Request:
		!! must login first, with password and username, so the Request can be done from the same session cookies
		example url:
		https://site.com/api/method/erpnext.smart_fm.api.qrcode?qr=QR94223256&id=4703163a

		It will return JSON data
	"""
	
	if frappe.db.exists("QRCode Data", code):
		doc = frappe.get_doc("QRCode Data", code)
		return doc.get_data()
	else:
		return 
