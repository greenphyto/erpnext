# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import xmltodict
import base64

class UOBFileLog(Document):
	def sync_payment_status(self, file, filename, raw=False):
		if "PA213" not in filename:
			return
		
		# get XML
		data = None
		if not raw:
			file_path = frappe.get_site_path(file.file_url.strip("/"))
			with open(file_path, 'r', encoding='utf-8') as f:
				data = xmltodict.parse(f.read())
		else:
			xml_bytes = base64.b64decode(file)
			xml_text = xml_bytes.decode("utf-8")
			data = xmltodict.parse(xml_text)

		if not data:
			return
		
		ProcessID = 0
		# default step number: L1,L2,L3,L4
		if "_1" in filename:
			ProcessID = 1
		elif "R1" in filename:
			ProcessID = 2
		elif "A1" in filename:
			ProcessID = 3
		elif "O1001" in filename:
			ProcessID = 4
		
		if not ProcessID:
			return
		

		
		payment_id = get_nested(data, ["Document", "CstmrPmtStsRpt", "OrgnlPmtInfAndSts", "OrgnlPmtInfId"])
		if frappe.db.exists(payment_id):

		# data['Document']['CstmrPmtStsRpt']['OrgnlPmtInfAndSts']['OrgnlPmtInfId']
		# read XML

		# get the payment number
		# match status
		# update payment
			pass

def get_nested(data, keys, default=None):
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data
