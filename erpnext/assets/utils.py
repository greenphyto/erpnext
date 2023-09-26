import frappe, json
from frappe.utils import getdate, cint, get_url, cstr
from pyqrcode import create as qrcreate
from io import BytesIO
from base64 import b32encode, b64encode


@frappe.whitelist()
def get_qrcode(data={}, doctype=None, docname=None, get_link=False, commit=False):
	# to generate qr code and store to QRCode Data
	# return base64 string images
	if not data and not doctype and not docname:
		return ''
	
	def get_link_detail(doc_name):
		ids = frappe.generate_hash(length=8)
		params = "qr={}&id={}".format(doc_name, ids)
		link = get_url("/api/method/erpnext.smart_fm.api.qrcode?{}".format(params))
		return link

	result_name = ""
	if data:
		# find exists
		data_temp = json.dumps(data, sort_keys=True)
		exists = frappe.db.exists("QRCode Data", {"data":data_temp})
		if exists:
			result_name = exists
		else:
			doc = frappe.new_doc("QRCode Data")
			doc.data = data
			doc.insert(ignore_permissions=True)
			result_name = doc.name

	elif doctype and docname:
		exists = frappe.db.exists("QRCode Data", {"doc_type":doctype, "doc_name":docname})
		if exists:
			result_name = exists
		else:
			doc = frappe.new_doc("QRCode Data")
			doc.doc_type = doctype
			doc.doc_name = docname
			doc.insert(ignore_permissions=True)
			result_name = doc.name
	else:
		return ""
	
	link = get_link_detail(result_name)
	if get_link:
		return link

	if commit:
		frappe.db.commit()
	
	# get base 64 string images
	img_string = get_qr_svg_code(link)
	return cstr(img_string)	

def get_qr_svg_code(totp_uri):
	"""Get SVG code to display Qrcode for OTP."""
	url = qrcreate(totp_uri)
	svg = ""
	stream = BytesIO()
	try:
		url.svg(stream, scale=4, background="#fff", module_color="#222")
		svg = stream.getvalue().decode().replace("\n", "")
		svg = b64encode(svg.encode())
	finally:
		stream.close()
	return svg

# use in doctype
def create_asset_qrcode(doc, method=""):
	if not doc.qrcode_image:
		url = save_qrcode_image(doc.doctype, doc.name, 1)
		doc.qrcode_image = url

import imgkit,base64
def save_qrcode_image(doctype, name, update_db=False):
	# get image qrcode
	# save to doctype
	url = get_url("/qrcode_preview?doctype={}&name={}".format(doctype, name))
	options = {'width': 600, 'disable-smart-width': ''}
	print("From url image", url)
	string_img = imgkit.from_url(url, False, options=options)
	encoded = base64.b64encode(string_img)

	# save file
	filenme= "QR Code - {} - {}.png".format(doctype, name)
	content = encoded
	is_private = 0
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filenme,
			"attached_to_doctype": doctype,
			"attached_to_name": name,
			"content": content,
			"decode": True,
			"is_private": is_private,
		}
	)
	file.save(ignore_permissions=True)
	file_url = file.file_url

	if doctype in ['Asset']:
		if update_db:
			frappe.db.set_value(doctype, name, "qrcode_image", file_url, update_modified=False)			

	return file_url