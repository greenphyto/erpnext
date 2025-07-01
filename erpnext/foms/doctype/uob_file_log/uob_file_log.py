# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import xmltodict
import base64

class UOBFileLog(Document):
	def sync_payment_status(self, file="", filename="", raw=False):
		if self.file:
			file = frappe.get_doc("File", self.file)
			filename = self.filename
			self._sync_payment_status(file, filename)
		else:
			self._sync_payment_status(file, filename, raw=True)

	def _sync_payment_status(self, file, filename="", raw=False):
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
		
		def convert_inv_no(inv_txt):
			part, yymm = inv_txt.split("-")
			year = "20" + yymm[:2]
			formatted = f"{part}/{year}"
			return formatted

		transactions = []
		txs = get_nested(data, ["Document", "CstmrPmtStsRpt", "OrgnlPmtInfAndSts", "TxInfAndSts"]) or []
		if txs and isinstance(txs, dict):
			txs = [txs]

		for tx in txs:
			invoice_no = convert_inv_no(tx["OrgnlEndToEndId"])
			dt = {
				"result":tx["TxSts"],
				"invoice_no": invoice_no,
				"account_no": tx["OrgnlTxRef"]["CdtrAcct"]["Id"]["Othr"]["Id"],
				"error_code": tx["StsRsnInf"]["Rsn"]["Cd"]
			}
			transactions.append(dt)
		
		payment_id = get_nested(data, ["Document", "CstmrPmtStsRpt", "OrgnlPmtInfAndSts", "OrgnlPmtInfId"])
		payment_id = payment_id.replace("PAY", "PAY-")
		# get the payment number
		if not frappe.db.exists("Payment Approval", payment_id):
			return

		doc = frappe.get_doc("Payment Approval", payment_id)
		doc.update_payment_status(ProcessID, transactions)
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
