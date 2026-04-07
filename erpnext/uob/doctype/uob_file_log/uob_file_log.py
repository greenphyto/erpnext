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
		
		# default step number: L1,L2,L3,L4
		ProcessID = get_process_id(filename)
		
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

		self.db_set("payment_approval", doc.name)
		doc.update_payment_status(ProcessID, transactions, file_date=file_date, error_message=error_message)

	def sync_payment_entry2(self, file, filename="", raw=False):
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
		single_charge_map = []
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
				if not temp:
					continue
				paid_amount = flt(temp.get("amount"))
				has_return = temp.get("has_return")

				if has_return and not "status_result" in x:
					# forbidden payment entry if has return but not have L4
					if paid_amount > 0:
						bank_account_no = frappe.get_value("Bank Account", pay_doc.bank_account, "bank_account_no")
						single_charge_map.append({
							"amount": paid_amount,
							"account": default_charge_account,
							"cost_center": cost_center_charge,
							"description": f"Bank Charge for {x['invoice_no']}",
							"company": pay_doc.company,
							"bank_account": pay_doc.account,
							"bank_account_no": bank_account_no,
							"payment_approval": pay_doc.name,
							"posting_date": getdate(),
							"filename": filename
						})
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
							temp = None
							if len(d['charges']) > i:
								charge = d['charges']
								temp = charge.iloc[0] if isinstance(charge, pd.Series) else charge[i]
							
							fee_rate = flt(temp['Transaction Amount']) if temp is not None else 0

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

		if single_charge_map:
			self.create_journal_entry(single_charge_map)

		for d in approval_update.values():
			d['doc'].update_payment_status(4, d['trans'])

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
		net_amount_mapping = get_net_amount_per_invoice(df_tx)
		"""
		net_amount_mapping = {
			"PAY-260045": {
				# if success
				"INV001":{
					"amount": 100,
					"fee": 2
				},
				# if return all
				"INV002":{
					"amount": 0,
					"fee": 0
				},
				# if only fee
				"INV001":{
					"amount": 0,
					"fee": 2
				}
			}
		}
		"""

		pe_map = {}
		approval_update = {}
		single_charge_map = []
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
				if not temp:
					continue
				paid_amount = flt(temp.get("amount"))
				has_return = temp.get("has_return")

				if has_return and not "status_result" in x:
					# forbidden payment entry if has return but not have L4
					if paid_amount > 0:
						bank_account_no = frappe.get_value("Bank Account", pay_doc.bank_account, "bank_account_no")
						single_charge_map.append({
							"amount": paid_amount,
							"account": default_charge_account,
							"cost_center": cost_center_charge,
							"description": f"Bank Charge for {x['invoice_no']}",
							"company": pay_doc.company,
							"bank_account": pay_doc.account,
							"bank_account_no": bank_account_no,
							"payment_approval": pay_doc.name,
							"posting_date": getdate(),
							"filename": filename
						})
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
							temp = None
							if len(d['charges']) > i:
								charge = d['charges']
								temp = charge.iloc[0] if isinstance(charge, pd.Series) else charge[i]
							
							fee_rate = flt(temp['Transaction Amount']) if temp is not None else 0

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

		if single_charge_map:
			self.create_journal_entry(single_charge_map)

		for d in approval_update.values():
			d['doc'].update_payment_status(4, d['trans'])

	def create_journal_entry(self, charges):
		"""Create journal entry for bank charges when transaction fails but charge is still deducted"""
		if not charges:
			return

		# Group charges by company and bank account
		from collections import defaultdict
		grouped_charges = defaultdict(list)
		
		for charge in charges:
			key = (charge.get('company'), charge.get('bank_account'), charge.get('posting_date'), charge.get('filename'))
			grouped_charges[key].append(charge)
		
		# Create separate JE for each group
		for (company, bank_account, posting_date, filename), charge_list in grouped_charges.items():
			je = frappe.new_doc("Journal Entry")
			je.posting_date = posting_date or getdate()
			je.voucher_type = "Bank Entry"
			je.company = company
			je.cheque_no = filename.replace(".csv", "") if filename else ""
			je.cheque_date = posting_date or getdate()
			
			total_debit = 0
			cost_center = ""
			payment_approval_list = []
			bank_account_no = ""
			
			# Add debit entries for bank charges
			for d in charge_list:
				amount = flt(d.get('amount', 0))
				if amount > 0:
					je.append("accounts", {
						"account": d.get('account'),
						"debit_in_account_currency": amount,
						"debit": amount,
						"cost_center": d.get('cost_center'),
						"reference_detail_no": d.get('payment_approval'),
						"user_remark": d.get('description', '')
					})
					cost_center = d.get('cost_center') or cost_center
					total_debit += amount
					
					# Collect payment approval for parent remark
					pay_app = d.get('payment_approval')
					if pay_app and pay_app not in payment_approval_list:
						payment_approval_list.append(pay_app)
					
					# Get bank account number
					if not bank_account_no:
						bank_account_no = d.get('bank_account_no', '')
			
			# Add credit entry for bank account
			if total_debit > 0:
				je.append("accounts", {
					"account": bank_account,
					"credit_in_account_currency": total_debit,
					"credit": total_debit,
					"cost_center": cost_center,
					"user_remark": f"Bank charges for failed transactions (Total: {total_debit})"
				})
				
				# Set parent user_remark with comprehensive info
				payment_list_str = ", ".join(payment_approval_list)
				je.user_remark = f"""Bank Charges - Failed Transactions
Bank Account: {bank_account_no or 'N/A'}
Payment Approval: {payment_list_str}
Date: {posting_date.strftime('%d-%m-%Y') if posting_date else getdate().strftime('%d-%m-%Y')}
Total Charges: {frappe.utils.fmt_money(total_debit, currency=frappe.get_cached_value('Company', company, 'default_currency'))}"""
				
				try:
					je.flags.ignore_validate = 1
					je.save(ignore_permissions=True)
				except Exception as e:
					frappe.log_error(f"Failed to create journal entry for bank charges: {str(e)}")

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
			d['pay_no'] = pay_name
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
		RETURN = {
			"PAY-260045": {
				# if success
				"INV001":{
					"amount": 100,
					"fee": 2
				},
				# if return all
				"INV002":{
					"amount": 0,
					"fee": 0
				},
				# if only fee
				"INV001":{
					"amount": 0,
					"fee": 2
				}
			}
		}
	"""
	df = df.copy()

	df["Base Transaction Code"] = df["Base Transaction Code"].astype(str).str.strip()
	df["Your Reference"]        = df["Your Reference"].astype(str).str.strip()
	df["Transaction Amount"]    = df["Transaction Amount"].apply(clean_amount)

	df = df[df["Your Reference"].str.startswith("PAY", na=False)]
	df["Your Reference"] = df["Your Reference"].apply(convert_inv_no)

	# distribute charges
	fee_map = {}
	"""
	fee_map = {
		"PAY-260045": 0.6,
		"PAY-260046": 10,
	}
	"""
	for index, row in df.iterrows():
		if row['Base Transaction Code'] == "D" and row['Transaction Description'] in ("SVC Chg", "SERV CHARGE"):
			if row['Your Reference'] not in fee_map:
				fee_map[row['Your Reference']] = 0
			fee_map[row['Your Reference']] += flt(row["Transaction Amount"])
	# prorate
	for key, value in fee_map.items():
		inv_count = frappe.db.count("Payment Invoice List", {"parent": key, "selected": 1})
		if inv_count > 0:
			fee_map[key] = round(value/inv_count, 2)

	result = {}
	for ref in df["Your Reference"].unique():
		inv_count = frappe.db.count("Payment Invoice List", {"parent": ref, "selected": 1})
		subset     = df[df["Your Reference"] == ref]
		debit      = subset[subset["Base Transaction Code"] == "D"]["Transaction Amount"].sum()
		credit     = subset[subset["Base Transaction Code"] == "C"]["Transaction Amount"].sum()
		has_return = not subset[subset["Base Transaction Code"] == "C"].empty
		fee = fee_map.get(ref, 0)
		total_fee = fee * inv_count
		result[ref] = {
			"amount":     round(debit - credit, 2)-total_fee,
			"total_fee": total_fee,
			"has_return": has_return,
			"fee": fee_map.get(ref, 0)
		}

	return result

def get_net_amount_per_invoice(df: pd.DataFrame) -> dict:
	"""
	Map amount per invoice based on CSV transactions and L4 status
	RETURN = {
		"PAY-260045": {
			"INV001": {
				"amount": 50.00,
				"fee": 1.00,
				"status": "ACCP"
			},
			"INV002": {
				"amount": 50.00,
				"fee": 1.00,
				"status": "ACCP"
			},
			"INV003": {
				"amount": 0,
				"fee": 0,
				"status": "RJCT"
			}
		}
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
		if not frappe.db.exists("Payment Approval", ref):
			continue
			
		# Get net amount summary
		subset = df[df["Your Reference"] == ref]
		debit = subset[subset["Base Transaction Code"] == "D"]["Transaction Amount"].sum()
		credit = subset[subset["Base Transaction Code"] == "C"]["Transaction Amount"].sum()
		has_return = not subset[subset["Base Transaction Code"] == "C"].empty
		
		# Calculate total service charges
		charges_rows = subset[
			(subset["Base Transaction Code"] == "D") & 
			(subset["Transaction Description"].isin(["SVC Chg", "SERV CHARGE"]))
		]
		total_fee = charges_rows["Transaction Amount"].sum()
		
		# Calculate net amount after deducting charges
		net_amount = round(debit - credit - total_fee, 2)
		
		# Get L4 status for invoices
		l4_status = get_uob_initiated_status(ref)
		invoice_status = l4_status.get(ref, {})
		
		# Get invoice list from Payment Approval
		doc = frappe.get_doc("Payment Approval", ref)
		invoice_list = [d for d in doc.get("invoices") if cint(d.selected)]
		
		if not invoice_list:
			continue
		
		# Count accepted invoices (status ACCP in L4)
		accepted_invoices = []
		for inv in invoice_list:
			inv_status = invoice_status.get(inv.invoice_no, {})
			l4_status_code = inv_status.get("4")  # L4 status
			
			# Consider as accepted if L4 status is ACCP or if no L4 data yet
			if l4_status_code == "ACCP" or (not l4_status_code and not has_return):
				accepted_invoices.append(inv)
		
		# If no accepted invoices but net_amount > 0, distribute to all (backwards compatibility)
		if not accepted_invoices and net_amount > 0:
			accepted_invoices = invoice_list
		
		# Calculate per-invoice fee
		fee_per_invoice = round(total_fee / len(invoice_list), 2) if invoice_list else 0
		
		# Distribute net amount to accepted invoices
		result[ref] = {}
		
		if accepted_invoices and net_amount > 0:
			# Get total of accepted invoice amounts
			total_accepted_amount = sum(flt(inv.amount) for inv in accepted_invoices)
			
			if total_accepted_amount > 0:
				# Distribute proportionally
				remaining_amount = net_amount
				for idx, inv in enumerate(accepted_invoices):
					if idx == len(accepted_invoices) - 1:
						# Last invoice gets remaining amount (to handle rounding)
						allocated_amount = remaining_amount
					else:
						# Proportional allocation
						ratio = flt(inv.amount) / total_accepted_amount
						allocated_amount = round(net_amount * ratio, 2)
						remaining_amount -= allocated_amount
					
					result[ref][inv.invoice_no] = {
						"amount": allocated_amount,
						"fee": fee_per_invoice,
						"status": "ACCP",
						"original_amount": flt(inv.amount)
					}
			else:
				# Equal distribution if amounts are same or zero
				amount_per_invoice = round(net_amount / len(accepted_invoices), 2)
				remaining = net_amount
				
				for idx, inv in enumerate(accepted_invoices):
					if idx == len(accepted_invoices) - 1:
						allocated_amount = remaining
					else:
						allocated_amount = amount_per_invoice
						remaining -= allocated_amount
					
					result[ref][inv.invoice_no] = {
						"amount": allocated_amount,
						"fee": fee_per_invoice,
						"status": "ACCP",
						"original_amount": flt(inv.amount)
					}
		
		# Add rejected invoices with zero amount
		for inv in invoice_list:
			if inv.invoice_no not in result[ref]:
				inv_status = invoice_status.get(inv.invoice_no, {})
				l4_status_code = inv_status.get("4", "UNKNOWN")
				
				result[ref][inv.invoice_no] = {
					"amount": 0,
					"fee": fee_per_invoice if l4_status_code == "RJCT" else 0,
					"status": l4_status_code,
					"original_amount": flt(inv.amount)
				}
	
	return result

def get_process_id(filename):
	if "_1" in filename:
		ProcessID = 1
	elif "R1" in filename:
		ProcessID = 2
	elif "A1" in filename:
		ProcessID = 3
	elif "O1001" in filename:
		ProcessID = 4
	return ProcessID

def get_uob_initiated_status(pay_no):
	# get L0,1,2,3,4 status from initaed file
	"""
	return {
		"PAY-260045": {
			"INV01": {
				"1": "ACCP",
				"2": "ACCP",
				"3": "ACCP",
				"4": "ACCP",
			},
			"INV02": {
				"1": "RJCT",
				"2": "RJCT",
				"3": "RJCT",
				"4": "RJCT",
			}
		}
	}
	"""
	result = {
		pay_no:{}
	}
	if not frappe.db.exists("Payment Approval", pay_no):
		return result
	
	# Get Payment Approval document and invoice groups once
	doc = frappe.get_doc("Payment Approval", pay_no)
	invoice_group = doc.get_invoice_group()
	
	logs = frappe.db.sql("select name, filename, file from `tabUOB File Log` where payment_approval = %s", (pay_no,), as_dict=1)
	for temp in logs:
		# load xml and parse
		file_url = frappe.db.get_value("File", temp["file"], "file_url")
		file_path = frappe.get_site_path(file_url.strip("/"))
		with open(file_path, 'r', encoding='utf-8') as f:
			data = xmltodict.parse(f.read()) 
		
		process_id = get_process_id(temp["filename"])
		if process_id in (1,3):
			# For L1 and L3, status is at group level (applies to all transactions)
			status = get_nested(data, ['Document','CstmrPmtStsRpt','OrgnlGrpInfAndSts','GrpSts'])
			for d in invoice_group:
				# Apply status to all invoices in this group
				for inv in d.get("invoices", []):
					key = inv.invoice_no
					result[pay_no].setdefault(key, {})
					result[pay_no][key].setdefault(str(process_id), status)
		elif process_id==4:
			# For L4, get transaction list once
			tx_list = get_nested(data, ['Document','CstmrPmtStsRpt','OrgnlPmtInfAndSts','TxInfAndSts'])
			if isinstance(tx_list, dict):
				tx_list = [tx_list]
			
			if tx_list:
				# Create mapping from batch_id to invoice_group
				# batch_id format: PAY260082A, PAY260082B, etc.
				batch = pay_no.replace("-", "")  # PAY-260082 -> PAY260082
				batch_to_group = {}
				for idx, d in enumerate(invoice_group):
					batch_id = batch + get_alpha_suffix(idx)
					batch_to_group[batch_id] = d
				
				# Match transactions by OrgnlInstrId
				for tx in tx_list:
					orgn_instr_id = tx.get("OrgnlInstrId")
					status = tx.get("TxSts")
					
					if orgn_instr_id and orgn_instr_id in batch_to_group:
						d = batch_to_group[orgn_instr_id]
						# Apply status to all invoices in this group
						for inv in d.get("invoices", []):
							key = inv.invoice_no
							result[pay_no].setdefault(key, {})
							result[pay_no][key].setdefault(str(process_id), status)

	return result

def get_alpha_suffix(index):
	"""
	Convert index to alphabetical suffix
	0 = A, 1 = B, ... 25 = Z, 26 = AA, 27 = AB, ...
	"""
	result = ""
	index += 1  
	while index > 0:
		index, remainder = divmod(index - 1, 26)
		result = chr(ord('A') + remainder) + result
	return result
