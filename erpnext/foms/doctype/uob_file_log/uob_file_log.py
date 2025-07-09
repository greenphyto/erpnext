# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import xmltodict
import base64
import pandas as pd
import io
from typing import Tuple, Optional, Union
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.utils import flt, cint, getdate, cstr
import datetime

class UOBFileLog(Document):
	def sync_payment_status(self, file="", filename="", raw=False):
		if self.file:
			file = frappe.get_doc("File", self.file)
			filename = self.filename
			self._sync_payment_status(file, filename)
			self.sync_payment_entry(file, filename)
		else:
			self._sync_payment_status(file, filename, raw=True)
			self.sync_payment_entry(file, filename, raw=True)

	def get_file_data(self, file, typ="XML", raw=False):
		# get XML
		data = None
		if not raw:
			file_path = frappe.get_site_path(file.file_url.strip("/"))
			if typ == "XML":
				with open(file_path, 'r', encoding='utf-8') as f:
					data = xmltodict.parse(f.read())
			else:
				return self.parse_uob_statement(file_path=file_path)
				# data = pd.read_csv(file_path)
				# data.columns = data.columns.str.replace(r'[\t\r\n]', '', regex=True).str.strip()

		else:
			if typ == "XML":
				file_bytes = base64.b64decode(file)
				file_text = file_bytes.decode("utf-8")
				data = xmltodict.parse(file_text)
			else:
				return self.parse_uob_statement(base64_file_str=file)

		return data
	
	def parse_uob_statement(self, 
			base64_file_str: Optional[str] = None,
			file_path: Optional[Union[str, io.TextIOWrapper]] = None
		) -> Tuple[pd.DataFrame, pd.DataFrame]:
		df_acc = pd.DataFrame()
		df_tx = pd.DataFrame()
		# Decode base64 ke string teks
		if base64_file_str:
			file_bytes = base64.b64decode(base64_file_str)
			file_text = file_bytes.decode("utf-8", errors="ignore")
		elif file_path:
			with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
				file_text = f.read()
		else:
			return df_acc, df_tx

		lines = file_text.splitlines()

		tx_start = None
		for i, line in enumerate(lines):
			if "Transaction Amount" in line:
				tx_start = i
				break

		if tx_start:
			acc_part = lines[:tx_start]
			acc_data = [line.split(",") for line in acc_part if "," in line]

			if len(acc_data) >= 2:
				df_acc = pd.DataFrame([dict(zip(acc_data[0], acc_data[1]))])
			else:
				df_acc = pd.DataFrame()

			tx_csv = "\n".join(lines[tx_start:])
			df_tx = pd.read_csv(io.StringIO(tx_csv))
			df_tx.columns = df_tx.columns.str.strip()  # bersihkan nama kolom

		return df_acc, df_tx

	def _sync_payment_status(self, file, filename="", raw=False):
		if "PA213" not in filename:
			return
		
		data = self.get_file_data(file, "XML", raw)
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

		transactions = []
		txs = get_nested(data, ["Document", "CstmrPmtStsRpt", "OrgnlPmtInfAndSts", "TxInfAndSts"]) or []
		if txs and isinstance(txs, dict):
			txs = [txs]

		for tx in txs:
			temp = tx.get("OrgnlEndToEndId")
			if temp:
				invoice_no = convert_inv_no(temp)
				error_code = get_nested(tx, ["StsRsnInf", "Rsn", "Cd"] )
				dt = {
					"result":tx["TxSts"],
					"invoice_no": invoice_no,
					"account_no": tx["OrgnlTxRef"]["CdtrAcct"]["Id"]["Othr"]["Id"],
					"error_code": error_code
				}
				transactions.append(dt)

		# Additional Information
		file_date = get_nested(data, ["Document", "CstmrPmtStsRpt", "GrpHdr", "CreDtTm"]) or ""
		temp = get_nested(data, [
			'Document', 
			'CstmrPmtStsRpt', 
			'OrgnlGrpInfAndSts', 
			'StsRsnInf', 
			'AddtlInf'
		], collect_multiple=True) or []
		error_message = "\n".join(temp)
			
		# Get Payment Approval
		temp = get_nested(data, ["Document", "CstmrPmtStsRpt", "OrgnlGrpInfAndSts", "OrgnlMsgId"]) or ""
		payment_id = frappe.db.get_value("Payment Approval", {"file_id":temp})
		# get the payment number
		if not payment_id:
			return

		doc = frappe.get_doc("Payment Approval", payment_id)
		doc.update_payment_status(ProcessID, transactions, file_date=file_date, error_message=error_message)


	def sync_payment_entry(self, file, filename="", raw=False):
		if "ES3_" not in filename:
			return
		
		df_acc, df_tx = self.get_file_data(file, "CSV", raw)
		if df_tx is None or df_tx.empty:
			return

		# clean data
		df_tx["Cheque Number"] = df_tx["Cheque Number"].astype(str).str.strip('="')
		for d in ["Transaction Date", "Statement Date", "Value Date"]:
			df_tx[d] = (
				df_tx[d]
				.astype(str)
				.str.strip('="')
				.apply(lambda x: datetime.datetime.strptime(x, "%d/%m/%Y").date())
			)

		
		for idx, row in df_tx.iterrows():
			# get PI
			invoice_no = convert_inv_no(row["Your Reference"])
			pi_name = frappe.db.exists("Purchase Invoice", invoice_no)
			if not pi_name:
				continue
			
			docstatus, status = frappe.db.get_value("Purchase Invoice", pi_name, ["docstatus", "status"]) or (0, "")
			if docstatus != 1 or status == "Paid":
				continue
			
			cheque_no = None
			if flt(row["Cheque Number"]):
				cheque_no = row["Cheque Number"]
			
			# create PE
			pe = get_payment_entry(dt="Purchase Invoice", dn=pi_name)
			pe.bank_account = self.get_bank_account(row["Account Number"])
			pe.mode_of_payment = "Bank Draft"
			pe.paid_amount = flt(row["Transaction Amount"])
			pe.reference_no = cheque_no or row["Our Reference"]
			pe.bank = frappe.get_value("Bank Account", pe.bank_account, "bank")
			pe.reference_date = row["Transaction Date"]
			pe.additional_info = self.get_transfer_info(row)
			pe.auto_generated = 1
			pe.insert(ignore_permissions=1)
			pe.submit()

	def get_bank_account(self, account_no):
		bank_name = frappe.db.get_value("Bank Account", {"bank_account_no":account_no}, "name")
		return bank_name
	
	def clear_date_format(self, date_str):
		cleaned = date_str.strip('="')
		parsed_date = datetime.datetime.strptime(cleaned, "%d/%m/%Y").date()
		return getdate(parsed_date)
	
	def get_transfer_info(self, row):
		row["Statement Date"] = row["Statement Date"].strftime("%d-%m-%Y")
		row["Value Date"] = row["Value Date"].strftime("%d-%m-%Y")

		txt = f"""Statement Date: {row["Statement Date"]}
		Value Date: {row["Value Date"]}
		Transaction Description: {row["Transaction Description"]}
		Teller ID: {row["Teller ID"]}
		Remarks: {row["Remarks"]}"""
		txt = txt.replace("\t", "")
		return txt

def convert_inv_no(inv_txt):
	if "-" in inv_txt:
		part, yymm = inv_txt.split("-")
	else:
		part, yymm = inv_txt[:-4], inv_txt[-4:]
	year = "20" + yymm[:2]
	formatted = f"{part}/{year}"
	return formatted

def get_nested(data, keys, default=None, collect_multiple=False):
    for i, key in enumerate(keys):
        if isinstance(data, dict):
            data = data.get(key, default)
        elif isinstance(data, list):
            # If asked collect_multiple and this is the final stage
            if collect_multiple and i == len(keys) - 1:
                return [item.get(key, default) for item in data if isinstance(item, dict)]
            else:
                # Take the first element as default traversal
                data = data[0] if data else default
                if isinstance(data, dict):
                    data = data.get(key, default)
        else:
            return default
    return data
