import frappe, json
from six import string_types
from frappe.utils import get_url

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
	accept_header = frappe.get_request_header("Accept") or ""
	user_agent = frappe.get_request_header("User-Agent") or ""
	respond_as_json = (
		frappe.get_request_header("Accept")
		and (frappe.local.is_ajax or "application/json" in accept_header)
	)
	if not respond_as_json:
		web_access = ("Firefox", "Chrome", "Safari") 
		respond_as_json = not any(elem in user_agent for elem in web_access)
	
	if frappe.db.exists("QRCode Data", code):
		doc = frappe.get_doc("QRCode Data", code)
		if not respond_as_json:
			frappe.local.response["type"] = "redirect"
			frappe.local.response["location"] = get_url("/app/asset/{}".format(doc.doc_name))
		return doc.get_data()
	else:
		return {}
	
@frappe.whitelist()
def get_widget_settings(user):
	raw = frappe.db.get_value("Mobile Widget User", {"user":user}, "settings") or {}
	if not raw:
		return {}
	
	settings = json.loads(raw)
	return settings

@frappe.whitelist()
def save_widget_settings(user, data):
	if isinstance(data, string_types):
		data = json.loads(data)
		
	temp = frappe.db.exists("Mobile Widget User", {"user":user})
	if temp:
		doc = frappe.get_doc("Mobile Widget User", temp)
	else:
		doc = frappe.new_doc("Mobile Widget User")
		doc.user = user

	doc.settings = json.dumps(data)
	if doc.is_new():
		doc.insert()
	else:
		doc.save()


	return "Success"