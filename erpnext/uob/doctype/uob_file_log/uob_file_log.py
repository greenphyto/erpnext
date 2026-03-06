# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import xmltodict
import base64
import pandas as pd
import io, re
from typing import Tuple, Optional, Union
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.utils import flt, cint, getdate, cstr
import datetime
from erpnext.accounts.utils import get_company_default
import math

class UOBFileLog(Document):
	@frappe.whitelist()
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

		# Bagi menjadi baris-baris
		lines = file_text.splitlines()

		# Temukan indeks baris transaksi (yang mengandung "Transaction Amount")
		tx_start = None
		for i, line in enumerate(lines):
			if "Transaction Amount" in line:
				tx_start = i
				break

		if tx_start is None:
			return df_acc, df_tx

		# Bagian atas = data akun
		acc_part = lines[:tx_start]
		acc_data = [line.split(",") for line in acc_part if "," in line]

		if len(acc_data) >= 2:
			# Baris 0 = header, Baris 1 = data
			df_acc = pd.DataFrame([dict(zip(acc_data[0], acc_data[1]))])
		else:
			df_acc = pd.DataFrame()

		# Bagian bawah = transaksi
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

		file_date = get_nested(data, ["Document", "CstmrPmtStsRpt", "GrpHdr", "CreDtTm"]) or ""

		if txs:
			status_name = get_nested(data, ['Document','CstmrPmtStsRpt','OrgnlGrpInfAndSts','GrpSts'])
			error_code_group = get_nested(data, ['Document','CstmrPmtStsRpt','OrgnlGrpInfAndSts','StsRsnInf','Rsn','Cd'])
			reff_no = get_nested(data, ['Document','CstmrPmtStsRpt','GrpHdr','MsgId'])
			reff_date = get_nested(data, ['Document','CstmrPmtStsRpt','GrpHdr','CreDtTm'])
			remarks = get_nested(data, ['Document','CstmrPmtStsRpt','OrgnlPmtInfAndSts','OrgnlPmtInfId'])
			for tx in txs:
				temp = tx.get("OrgnlEndToEndId") or ""
				error_code = get_nested(tx, ["StsRsnInf", "Rsn", "Cd"] ) or error_code_group
				error_info = get_nested(tx, ["StsRsnInf", "AddtlInf"] ) or ""
				result = ""
				if ProcessID in [1,3]:
					result = status_name
					invoice_no = "*"
				else:
					invoice_no = convert_inv_no(temp)
					result = get_nested(tx, ["TxSts"])
				dt = {
					"result": result,
					"invoice_no": invoice_no,
					"bank_account": get_nested(tx, ['OrgnlTxRef','DbtrAcct','Id','Othr','Id']),
					"account_no": get_nested(tx, ["OrgnlTxRef","CdtrAcct","Id","Othr","Id"]) or "*",
					"error_code": error_code,
					"error_info": error_info,
					"amount": flt(get_nested(tx, ['OrgnlTxRef','Amt','InstdAmt','#text'])),
					"currency": get_nested(tx, ['OrgnlTxRef','Amt','InstdAmt','@Ccy']),
					"bic": get_nested(tx, ['OrgnlTxRef','CdtrAgt','FinInstnId','BIC']),
					"reff_no": reff_no,
					"reff_date": reff_date,
					"remarks": remarks,
				}
				transactions.append(dt)

			# Additional Information
			temp = get_nested(data, [
				'Document', 
				'CstmrPmtStsRpt', 
				'OrgnlGrpInfAndSts', 
				'StsRsnInf', 
				'AddtlInf'
			], collect_multiple=True) or []
			if type(temp) == list:
				error_message = "\n".join(temp)
			else:
				error_message = temp
				
			# Get Payment Approval
			temp = get_nested(data, ['Document','CstmrPmtStsRpt','OrgnlPmtInfAndSts','OrgnlPmtInfId']) or ""
			ids = convert_inv_no(temp)
			payment_id = frappe.db.get_value("Payment Approval", ids)
			# get the payment number
			if not payment_id:
				return

			doc = frappe.get_doc("Payment Approval", payment_id)
		else:
			temp = get_nested(data, ['Document','CstmrPmtStsRpt','OrgnlGrpInfAndSts','OrgnlMsgId']) or ""
			batch_no = cint(temp[-3:])
			payment_id = frappe.db.get_value("Payment Approval", {"batch_number":batch_no})
			# get the payment number
			if not payment_id:
				return
			doc = frappe.get_doc("Payment Approval", payment_id)
			result = get_nested(data, ['Document','CstmrPmtStsRpt','OrgnlGrpInfAndSts','GrpSts'])
			error_code = get_nested(data, ['Document','CstmrPmtStsRpt','OrgnlGrpInfAndSts','StsRsnInf','Rsn','Cd'])
			error_message = ", ".join(get_nested(data, ['Document','CstmrPmtStsRpt','OrgnlGrpInfAndSts','StsRsnInf','AddtlInf']) or [])
			for d in doc.get("invoices"):
				dt = {
						"result": result,
						"invoice_no": d.invoice_no,
						"account_no": d.bank_account_no,
						"error_code": error_code,
						"amount": d.amount,
						"currency": d.currency,
						"bic": d.swift,
						"remarks": error_message,
					}
				transactions.append(dt)

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

		trans_map = {}
		for idx, row in df_tx.iterrows():
			# get PI
			pay_name = convert_inv_no(row["Your Reference"])
			if not pay_name:
				continue
			
			if pay_name not in trans_map:
				trans_map[pay_name] = {
					"transfer":[],
					"charges":[]
				}
			
			# need key for bank account specific
			if row["Transaction Description"] in ("SVC Chg", "SERV CHARGE"):
				# charges
				trans_map[pay_name]['charges'].append(row)
			else:
				# transfer
				trans_map[pay_name]['transfer'].append(row)

		# get net amount mapping
		net_amount_mapping = get_net_amount(df_tx)

		pe_map = {}
		approval_update = {}
		for pay_name, d in trans_map.items():
			# if pay_name!= "PAY-260045":
			# 	continue
			pay_doc = frappe.get_doc("Payment Approval", pay_name)
			default_charge_account = get_company_default(pay_doc.company, "default_bank_charge_account")
			cost_center_charge = get_company_default(pay_doc.company, "cost_center")
			fee_rate = 0
			type_fee = 0
			invoice_group = self.get_l4_mapping(pay_name)
			trans_count = len(invoice_group.values())
			if len(d['charges']) == 1:
				# bulk charge
				total_fee = flt(d['charges'][0]['Transaction Amount'])
				fee_rate = round(total_fee/trans_count, 2)
				type_fee = "SUM"
			else:
				# individual charge
				type_fee = "IND"

			pe_name_list = []
			for x in invoice_group.values():
				if x.get("status_result") == "RJCT":
					continue
				
				temp = net_amount_mapping.get(x['pay_no'])
				paid_amount = flt(temp.get("amount"))
				has_return = temp.get("has_return")

				if has_return and not "status_result" in x:
					# forbidden payment entry if has return but not have L4
					continue

				for i, tr in enumerate(d['transfer']):
					if tr['Base Transaction Code'].strip() == "C":
						continue

					# based on value, its not not a good way, but temporary for current version
					for row in x['invoices']:

						pi_name = row.invoice_no
						supplier = row.party

						# use update amount value
						if paid_amount > row.amount:
							paid_amount -= row.amount
							amount = row.amount
						elif math.isclose(paid_amount, row.amount, abs_tol=0.1):
							paid_amount = 0
							amount = row.amount
						elif paid_amount == 0:
							amount = 0
							continue

						docstatus, status = frappe.db.get_value("Purchase Invoice", pi_name, ["docstatus", "status"]) or (0, "")
						if docstatus != 1 or status == "Paid":
							continue
						
						cheque_no = None
						if flt(tr["Cheque Number"]):
							cheque_no = tr["Cheque Number"]
						
						if type_fee == "IND":
							# get rate by same order with transaction - its not best practice, but temporary
							temp = d['charges'][i] if len(d['charges']) > i else None
							if temp:
								fee_rate = flt(temp['Transaction Amount'])
							else:
								fee_rate = 0

						if pay_doc.name not in approval_update:
							approval_update[pay_doc.name] = {
								"doc":pay_doc,
								"trans":[]
							}
						approval_update[pay_doc.name]['trans'].append({
							"account_no": row.bank_account_no,
							"amount": row.amount,
							"result": "ACCP",         
							"error_code": None        
						})
							
						key = (supplier, pay_doc.name)
						if key not in pe_map:
							filters = {"payment_approval":pay_doc.name, "docstatus":1, "party":supplier}
							# create PE based on same party/supplier
							# find submit version
							use_exists_pe = frappe.db.get_value("Payment Entry", filters, 'name')
							if use_exists_pe:
								continue

							# find draft
							filters['docstatus'] = 0
							use_exists_pe = frappe.db.get_value("Payment Entry", filters, 'name')				

							if not use_exists_pe:
								pe = get_payment_entry(dt="Purchase Invoice", dn=pi_name)
								pe.paid_amount = 0
								for drow in pe.get("references"):
									pe.remove(drow)
								pe.__newname = get_next_pay_name(pay_doc.name, pe_name_list)
								pe.name = pe.__newname
								pe.flags.name_set = True
								pe_name_list.append(pe.name)
							else:
								frappe.db.sql("delete from `tabPayment Entry Reference` where parent = %s ", use_exists_pe)
								pe = frappe.get_doc("Payment Entry", use_exists_pe)
								pe.paid_amount = 0

							payment_mode = get_payment_mode(pay_doc.company, pay_doc.account)
							pe_map[key] = pe
							pe.payment_approval = pay_doc.name
							pe.bank_account = pay_doc.bank_account
							pe.paid_from = pay_doc.account
							pe.mode_of_payment = payment_mode
							pe.reference_no = cheque_no or tr["Our Reference"]
							pe.bank = frappe.get_value("Bank Account", pe.bank_account, "bank")
							pe.reference_date = tr["Transaction Date"]
							pe.additional_info = self.get_transfer_info(tr)
							pe.auto_generated = 1
							row_id = cstr(tr['Internal Transaction Code']).replace('="', '').replace('"', '')

							# add charges
							if fee_rate:
								exists_row = pe.get("deductions", {"reff_id": row_id})
								if not exists_row:
									row = pe.append("deductions")
									row.update({
										"account": default_charge_account, 
										"cost_center": cost_center_charge,    
										"amount": fee_rate,
										"description": f"Bank Charge for {pi_name} - {tr['Transaction Description']}",
										"reff_id": row_id
									})
									pe.paid_amount += fee_rate

						
							# add invoice
							exists_row = pe.get("references", {"reff_id": row_id, "reference_name": pi_name})
							if not exists_row:
								row = pe.append("references")
								row.update({
									"reference_doctype": "Purchase Invoice",
									"reference_name": pi_name,
									"total_amount": amount,
									"outstanding_amount": amount,
									"allocated_amount": amount,
									"reff_id": row_id
								})
								pe.paid_amount += amount		
		
		for pe in pe_map.values():
			pe.flags.ignore_validate = 1
			pe.save(ignore_permissions=1)
			# pe.submit()

		for d in approval_update.values():
			d['doc'].update_payment_status(4, d['trans'])


	def get_bank_account(self, account_no):
		bank_name = frappe.db.get_value("Bank Account", {"bank_account_no":account_no}, "name")
		return bank_name
	
	def clear_date_format(self, date_str):
		cleaned = date_str.strip('="')
		parsed_date = datetime.datetime.strptime(cleaned, "%d/%m/%Y").date()
		return getdate(parsed_date)
	
	def get_transfer_info(self, row):
		row["Statement Date"] = getdate(row["Statement Date"]).strftime("%d-%m-%Y")
		row["Value Date"] = getdate(row["Value Date"]).strftime("%d-%m-%Y")

		txt = f"""Statement Date: {row["Statement Date"]}
		Value Date: {row["Value Date"]}
		Transaction Description: {row["Transaction Description"]}
		Teller ID: {row["Teller ID"]}
		Remarks: {row["Remarks"]}"""
		txt = txt.replace("\t", "")
		return txt

	def get_l4_mapping(self, pay_name):
		doc = frappe.get_doc("Payment Approval", pay_name)
		group_invoices = doc.get_invoice_group()
		date = getdate(doc.request_date)
		l4_log_name = find_uob_file_log( date.year, doc.batch_number)
		xml_content = None
		xml_map = {}
		if l4_log_name:
			l4_log = frappe.get_doc("UOB File Log", l4_log_name.name)
			file = frappe.get_doc("File", l4_log.file)
			xml_content = l4_log.get_file_data(file, "XML", False)

		if xml_content:
			xml_map = parse_xml_transactions(xml_content)
		
		res_map = {}
		for d in group_invoices:
			key = (d['bank_account_name'], d['bank_account_no'])
			if key in xml_map:
				result = xml_map.get(key)
				d['status_result'] = result['status']
			
			res_map[key] = d

		return res_map

import xml.etree.ElementTree as ET
def parse_xml_transactions(xml_content):
    # xml_content = hasil xmltodict.parse()
    tx_list = xml_content["Document"]["CstmrPmtStsRpt"]["OrgnlPmtInfAndSts"]["TxInfAndSts"]

    if isinstance(tx_list, dict):
        tx_list = [tx_list]

    result = {}

    for tx in tx_list:
        ref       = tx.get("OrgnlTxRef", {})
        amt_node  = ref.get("Amt", {}).get("InstdAmt", {})
        cdtr_nm   = ref.get("Cdtr", {}).get("Nm")
        cdtr_acct = ref.get("CdtrAcct", {}).get("Id", {}).get("Othr", {}).get("Id")

        key = (cdtr_nm, cdtr_acct)

        result[key] = {
            "orgn_instr_id": tx.get("OrgnlInstrId"),
            "status":        tx.get("TxSts"),
            "amount":        amt_node.get("#text") if isinstance(amt_node, dict) else amt_node,
            "currency":      amt_node.get("@Ccy")  if isinstance(amt_node, dict) else "",
        }

    return result

def find_uob_file_log(year, batch_no):
    year_2d  = str(year)[-2:]
    batch_3d = str(batch_no).zfill(3)

    like_pattern = f"%{year_2d}%{batch_3d}O1001%.xml"

    result = frappe.db.sql("""
        SELECT `name`, `filename`
        FROM `tabUOB File Log`
        WHERE `filename` LIKE %(pattern)s
        ORDER BY `modified` DESC
        LIMIT 1
    """, {"pattern": like_pattern}, as_dict=True)

    return result[0] if result else None

def convert_inv_no(inv_txt):
    inv_txt = inv_txt.strip()
    # not yet upgrade
    if "PAY" in inv_txt:
        # Strip trailing letter(s) seperti PAY260025A -> PAY260025
        base = inv_txt.rstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        return base.replace("PAY", "PAY-")
    elif inv_txt:
        if "-" in inv_txt:
            part, yymm = inv_txt.split("-")
        else:
            part, yymm = inv_txt[:-4], inv_txt[-4:]
        year = "20" + yymm[:2]
        formatted = f"{part}/{year}"
        return formatted

def get_next_pay_name(base_name, pe_name_list=None):
    existing_names = frappe.db.get_list(
        "Payment Entry",
        filters={"name": ["like", f"{base_name}%"]},
        pluck="name"
    ) + (pe_name_list or [])

    if not existing_names:
        return base_name

    max_suffix = 0
    base_exists = False

    for name in existing_names:
        match = re.match(rf"{re.escape(base_name)}-(\d+)$", name)
        if match:
            num = int(match.group(1))
            if num > max_suffix:
                max_suffix = num
        elif name == base_name:
            base_exists = True

    if not base_exists and max_suffix == 0:
        return base_name
    
    return f"{base_name}-{max_suffix + 1}"


def transform_code(code: str):
	# Pisahkan prefix, angka, dan suffix huruf
	match = re.match(r"(PAY)(\d+)([A-Z]+)", code)
	if not match:
		return None
	
	prefix, number, suffix = match.groups()
	
	# Ambil 2 digit pertama sebagai "YY"
	yy = number[:2]
	# Sisanya sebagai nomor urut, lalu pad ke 4 digit
	seq = int(number[2:]) if len(number) > 2 else 0
	seq_fmt = f"{seq:04d}"
	
	new_code = f"{prefix}-{yy}{seq_fmt}"
	return new_code, suffix

def get_inv_no(reff_no, amount):
	invoice_no = convert_inv_no(reff_no)
	if "PAY" in invoice_no and frappe.db.exists("Payment Approval", invoice_no):
		doc = frappe.get_doc("Payment Approval", invoice_no)
		for d in doc.get("invoices"):
			if flt(d.amount) == flt(amount):
				return d.invoice_no
	else:
		pi_name = frappe.db.exists("Purchase Invoice", invoice_no)
		return pi_name

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

def get_payment_mode(company, bank_account):
	data = frappe.db.sql("""
		SELECT 
			mopa.parent, mopa.default_account, mop.paynow
		FROM
			`tabMode of Payment Account` mopa
				INNER JOIN
			`tabMode of Payment` mop ON mop.name = mopa.parent
		WHERE
			mopa.default_account = %s
				AND mopa.company = %s
				AND mop.paynow = 1""", (bank_account, company), as_dict=1)
	if data:
		return data[0].parent
	return frappe.db.get_value("Mode of Payment", {"type": "Bank", "enabled":1}, "name")

def clean_amount(value) -> float:
    """Remove commas and Excel formula artifacts, convert to float."""
    if pd.isna(value):
        return 0.0
    value = re.sub(r'^="?(.*?)"?$', r'\1', str(value).strip())
    value = value.replace(",", "").strip()
    try:
        return float(value)
    except ValueError:
        return 0.0


def get_net_amount(df: pd.DataFrame) -> dict:
    """
    Returns:
        {
            "PAY-260044": {"amount": 37.50,   "has_return": False},
            "PAY-260045": {"amount": 2301.32, "has_return": True},
            ...
        }
    """
    df = df.copy()

    df["Base Transaction Code"] = df["Base Transaction Code"].astype(str).str.strip()
    df["Your Reference"]        = df["Your Reference"].astype(str).str.strip()
    df["Transaction Amount"]    = df["Transaction Amount"].apply(clean_amount)

    df = df[df["Your Reference"].str.startswith("PAY", na=False)]
    df["Your Reference"] = df["Your Reference"].apply(convert_inv_no)

    result = {}
    for ref in df["Your Reference"].unique():
        subset     = df[df["Your Reference"] == ref]
        debit      = subset[subset["Base Transaction Code"] == "D"]["Transaction Amount"].sum()
        credit     = subset[subset["Base Transaction Code"] == "C"]["Transaction Amount"].sum()
        has_return = not subset[subset["Base Transaction Code"] == "C"].empty
        result[ref] = {
            "amount":     round(debit - credit, 2),
            "has_return": has_return,
        }

    return result