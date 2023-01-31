# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from inspect import _void
import json

import frappe
from frappe import _
from frappe.contacts.report.addresses_and_contacts import test_addresses_and_contacts
from frappe.utils import formatdate, get_link_to_form, flt,fmt_money


def execute(filters=None):

	return VATAuditReport(filters).run()


class VATAuditReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.columns = []
		self.data = []
		self.doctypes = ["Sales Invoice","Purchase Invoice"]

	def run(self):
		#self.get_sa_vat_accounts()
		self.get_columns()
		gftotal_net = gstotal_net = gptotal_net = 0
		totalsstr = "Output Tax Due"
		totalpstr = "Less:Input Tax and Redunds claimed"
		totalfstr = "Equals: Net GST to be paid by you or <br>Net GST to be claimed by you"
		for doctype in self.doctypes:
			self.select_columns = """
			name as voucher_no,
			taxes_and_charges,
			posting_date, remarks"""
			columns = (
				", supplier as party, credit_to as account, bill_no as Invoice_No"
				if doctype == "Purchase Invoice"
				else ", customer as party, debit_to as account, name as Invoice_No"
			)
			self.select_columns += columns

			self.get_invoice_data(doctype)

			if self.invoices:
				self.get_invoice_items(doctype)
				self.get_items_based_on_tax_rate(doctype)
				self.get_data(doctype)
				taxdata = self.data
			
				if doctype == "Purchase Invoice" :
					gptotal_net = taxdata[-2]["tax_amount"]
				if doctype == "Sales Invoice" :
					gstotal_net = taxdata[-2]["tax_amount"]
				#print(test[-2]["tax_amount"])
		gftotal_net=( 0.0 if flt(gstotal_net) =="" else flt(gstotal_net)  )- ( 0.0 if flt(gptotal_net) =="" else flt(gptotal_net)  )  
		gstotal = {
				"posting_date":  totalsstr,
				"gross_amount": '',
				"tax_amount": '',
				"tax_amount": fmt_money(gstotal_net),
				"bold": 0,
			}
		gptotal = {
				"posting_date": totalpstr,
				"gross_amount": '',
				"tax_amount": '',
				"tax_amount": fmt_money(gptotal_net),
				"bold": 0,
			}
		gftotal = {
				"posting_date": totalfstr,
				"gross_amount": '',
				"tax_amount": '',
				"tax_amount": fmt_money(gftotal_net ),
				"bold": 0,
			}
		self.data.append(gstotal)
		self.data.append(gptotal)
		self.data.append(gftotal)
		
		return self.columns, self.data

	# def get_sa_vat_accounts(self):
	# 	self.sa_vat_accounts = frappe.get_all(
	# 		"South Africa VAT Account", filters={"parent": self.filters.company}, pluck="account"
	# 	)
	# 	if not self.sa_vat_accounts and not frappe.flags.in_test and not frappe.flags.in_migrate:
	# 		link_to_settings = get_link_to_form(
	# 			"South Africa VAT Settings", "", label="South Africa VAT Settings"
	# 		)
	# 		frappe.throw(_("Please set VAT Accounts in {0}").format(link_to_settings))

	def get_invoice_data(self, doctype):
		conditions = self.get_conditions()
		self.invoices = frappe._dict()

		invoice_data = frappe.db.sql(
			"""
			SELECT
				{select_columns}
			FROM
				`tab{doctype}`
			WHERE
				docstatus = 1 {where_conditions}
				and is_opening = 'No'
			ORDER BY
				posting_date DESC
			""".format(
				select_columns=self.select_columns, doctype=doctype, where_conditions=conditions
			),
			self.filters,
			as_dict=1,
		)

		for d in invoice_data:
			self.invoices.setdefault(d.voucher_no, d)

	def get_invoice_items(self, doctype):
		self.invoice_items = frappe._dict()
#, is_zero_rated
		items = frappe.db.sql(
			"""
			SELECT
				item_code, parent, base_net_amount
			FROM
				`tab%s Item`
			WHERE
				parent in (%s)
			"""
			% (doctype, ", ".join(["%s"] * len(self.invoices))),
			tuple(self.invoices),
			as_dict=1,
		)
		for d in items:
			self.invoice_items.setdefault(d.parent, {}).setdefault(d.item_code, {"net_amount": 0.0})
			self.invoice_items[d.parent][d.item_code]["net_amount"] += d.get("base_net_amount", 0)
		##	self.invoice_items[d.parent][d.item_code]["is_zero_rated"] = d.is_zero_rated
	def get_tax_types(self, doctype):
		tax_type = frappe._dict()
		tax_doctype = (
			"Purchase Taxes and Charges" if doctype == "Purchase Invoice" else "Sales Taxes and Charges"
		)
#, is_zero_rated
		items = frappe.db.sql(
			"""
			SELECT
				rate, parent
			FROM
				`tab{doc_type}`
			WHERE
				parenttype = "{doc_type} Template"
			""".format(
				  doc_type=tax_doctype
			),
			as_dict=1,
		)
	 
		return items	

	def get_items_based_on_tax_rate(self, doctype):
		self.items_based_on_tax_rate = frappe._dict()
		self.item_tax_rate = frappe._dict()
		self.tax_doctype = (
			"Purchase Taxes and Charges" if doctype == "Purchase Invoice" else "Sales Taxes and Charges"
		)

		self.tax_details = frappe.db.sql(
			"""
			SELECT
				parent, account_head, item_wise_tax_detail
			FROM
				`tab%s`
			WHERE
				parenttype = %s and docstatus = 1
				and parent in (%s)
			ORDER BY
				account_head
			"""
			% (self.tax_doctype, "%s", ", ".join(["%s"] * len(self.invoices.keys()))),
			tuple([doctype] + list(self.invoices.keys())),
		)

		for parent, account, item_wise_tax_detail in self.tax_details:
			if item_wise_tax_detail:
				try:
					# if account in self.sa_vat_accounts:
					# 	item_wise_tax_detail = json.loads(item_wise_tax_detail)
					# else:
					# 	continue
					item_wise_tax_detail = json.loads(item_wise_tax_detail)
					#print(item_wise_tax_detail)
					for item_code, taxes in item_wise_tax_detail.items():
						is_zero_rated = 0# self.invoice_items.get(parent).get(item_code).get("is_zero_rated")
						# to skip items with non-zero tax rate in multiple rows gf
						#if taxes[0] == 0 and not is_zero_rated:
							#continue
						tax_rate = self.get_item_amount_map(parent, item_code, taxes)

						if tax_rate is not None:
							rate_based_dict = self.items_based_on_tax_rate.setdefault(parent, {}).setdefault(
								tax_rate, []
							)
							if item_code not in rate_based_dict:
								rate_based_dict.append(item_code)
				except ValueError:
					continue

	def get_item_amount_map(self, parent, item_code, taxes):
		net_amount =self.invoice_items.get(parent).get(item_code).get("net_amount")
		tax_rate = taxes[0]
		tax_amount = taxes[1]
		gross_amount = net_amount + tax_amount


		self.item_tax_rate.setdefault(parent, {}).setdefault(
			item_code,
			{
				"tax_rate": tax_rate,
				"gross_amount": 0.0,
				"tax_amount": 0.0,
				"net_amount": 0.0,
				"parent":parent,
			},
		)

		self.item_tax_rate[parent][item_code]["net_amount"] += net_amount
		self.item_tax_rate[parent][item_code]["tax_amount"] += tax_amount
		self.item_tax_rate[parent][item_code]["gross_amount"] += gross_amount
		#print(tax_rate)
		return tax_rate

	def get_conditions(self):
		conditions = ""
		for opts in (
			("company", " and company=%(company)s"),
			("from_date", " and posting_date>=%(from_date)s"),
			("to_date", " and posting_date<=%(to_date)s"),
		):
			if self.filters.get(opts[0]):
				conditions += opts[1]

		return conditions

	def get_data(self, doctype):
		consolidated_data = self.get_consolidated_data(doctype)
		isloop = False
		section_name = _("Input tax/ Purchase tax") if doctype == "Purchase Invoice" else _("Output tax/ Sales tax")

		 
		gtotal_gross = gtotal_tax = gtotal_net = 0.0
		totalstr = " "
		for taxType, section in consolidated_data.items():
			#rate = int(rate)
			label = frappe.bold(section_name )
			section_head = {"posting_date": label}
			total_gross = total_tax = total_net = 0.0
			self.data.append(section_head) if isloop == False else  _void
			isloop = True
			for row in section.get("data"):
				if (self.filters.show_details):
					self.data.append(row)
				total_gross += 0 if  row["gross_amount"]=="" else flt(row["gross_amount"])
				total_tax += 0 if  row["tax_amount"] =="" else  flt(row["tax_amount"])
				total_net += 0 if row["net_amount"] =="" else flt(row["net_amount"])
			
			totalstr = _("Total value of taxable ") if doctype == "Purchase Invoice" else _("Total value of taxable ")
			doctypestr = _("Purchases") if doctype == "Purchase Invoice" else _("Sales")
			total = {
				"posting_date": totalstr + taxType,
				"gross_amount": fmt_money(total_gross),
				"tax_amount": fmt_money(total_tax),
				"net_amount": fmt_money(total_net),
				"bold": 0,
				#"voucher_type":"noclick",
			}
			
			self.data.append(total)
			gross_amount= 0.0 if  row["gross_amount"] =="" else flt(total["gross_amount"])
			gtotal_gross += gross_amount
			gtotal_tax +=  0.0 if  row["tax_amount"] =="" else flt(total["tax_amount"])
			gtotal_net +=  0.0 if  row["net_amount"] =="" else flt(total["net_amount"])
			
		gtotal = {
				"posting_date": totalstr + doctypestr,
				"gross_amount": fmt_money(gtotal_gross),
				"tax_amount": fmt_money(gtotal_tax),
				"net_amount": fmt_money(gtotal_net),
				"bold": 0,
				"voucher_type":doctype,
			}
		self.data.append(gtotal)
		self.data.append({}) #if doctype == "Purchase Invoice" else _void
	def get_consolidated_data(self, doctype):
		consolidated_data_map = {}
		for inv, inv_data in self.invoices.items():
			if self.items_based_on_tax_rate.get(inv):
				for rate, items in self.items_based_on_tax_rate.get(inv).items():
					row = {"tax_amount": 0.0, "gross_amount": 0.0, "net_amount": 0.0}
					docprefix = _("purchases ") if doctype == "Purchase Invoice" else _("sales ")
					taxdata ="" if  inv_data.get("taxes_and_charges") is None else inv_data.get("taxes_and_charges")
					taxType = docprefix + taxdata
					consolidated_data_map.setdefault(taxType, {"data": []})
					for item in items:
						item_details = self.item_tax_rate.get(inv).get(item)
						row["account"] = inv_data.get("account")
						row["Invoice_No"]= inv_data.get("Invoice_No")
						row["posting_date"] = inv#formatdate(inv_data.get("posting_date"), "dd-mm-yyyy")
						row["Date"] = formatdate(inv_data.get("posting_date"), "dd-mm-yyyy")
						#row["voucher_type"] = ""
						row["voucher_no"] = inv
						row["party_type"] = "Customer" if doctype == "Sales Invoice" else "Supplier"
						row["party"] = inv_data.get("party")
						row["remarks"] = inv_data.get("remarks")
					 
						rowgross_amount = flt(item_details.get("gross_amount"))
						row["gross_amount"] +=(rowgross_amount)
						row["gross_amount"] = fmt_money(row["gross_amount"] )
						row["tax_amount"] +=  item_details.get("tax_amount")
						row["tax_amount"] = fmt_money(row["tax_amount"] )
						row["net_amount"] += item_details.get("net_amount")
						row["net_amount"] = fmt_money(row["net_amount"] )

						row["tax_charge"] = inv_data.get("taxes_and_charges")
				 
					consolidated_data_map[taxType]["data"].append(row)
		get_tax_type = self.get_tax_types(doctype)
		
		for tax_type in get_tax_type:
			docprefix = _("purchases ") if doctype == "Purchase Invoice" else _("sales ")
			taxtype =docprefix +  tax_type.get("parent")
			 
			if (taxtype in consolidated_data_map):
				continue
			else:
				row = {"tax_amount": 0.0, "gross_amount": 0.0, "net_amount": 0.0}	 
				consolidated_data_map.setdefault(taxtype, {"data": []})
				row["account"] = ""
				row["posting_date"] =""
				row["voucher_type"] = ""
				row["voucher_no"] = ""
				row["party_type"] = "Customer" if doctype == "Sales Invoice" else "Supplier"
				row["party"] = ""
				row["remarks"] = ""
				row["gross_amount"] = ""
				row["tax_amount"] = ""
				row["net_amount"] = ""
				row["tax_charge"] = tax_type.get("parent")
				consolidated_data_map[taxtype]["data"].append(row)
		 
		return consolidated_data_map

	def get_columns(self):
		if (self.filters.show_details):
						self.columns +=[ 	{"fieldname": "party",
								"label": "Company",
								"fieldtype": "Data",
								"width": 140}]
		if (self.filters.show_details):
							self.columns +=[ {"fieldname": "Invoice_No",
							"label": "Invoice",
							"fieldtype": "Data",
							"width": 140}]
		if (self.filters.show_details):	
							self.columns +=[ {"fieldname": "Date",
							"label": "Date",
							"fieldtype": "Data",
							"width": 140}]
		self.columns += [
						

			{"fieldname": "posting_date", "label": " ", "fieldtype": "Link","options": "Account", "width": 350},
			{
				"fieldname": "account",
				"label": "Account",
				"fieldtype": "Link",
				"options": "Account",
				"width": 180,
				"hidden": 1
			},
			{
				"fieldname": "voucher_type",
				"label": "Voucher Type",
				"fieldtype": "Data",
				"width": 140,
				"hidden": 1
			},
			{
				"fieldname": "voucher_no",
				"label": "Reference",
				"fieldtype": "Dynamic Link",
				"options": "voucher_type",
				"width": 150,
				"hidden": 1
			},
			{
				"fieldname": "party_type",
				"label": "Party Type",
				"fieldtype": "Data",
				"width": 140,
				"hidden": 1
				 
			},
			{
				"fieldname": "party",
				"label": "Party",
				"fieldtype": "Dynamic Link",
				"options": "party_type",
				"width": 150,
				"hidden": 1
			},
			{"fieldname": "remarks", "label": "Details", "fieldtype": "Data", "width": 150,"hidden": 1},
			{"fieldname": "net_amount", "label": "Taxable Amount", "fieldtype": "Currency","options":"Company:company:default_currency", "width": 150},
			{"fieldname": "tax_amount", "label": "GST Amount", "fieldtype": "Currency","options":"Company:company:default_currency", "width": 150},
			{"fieldname": "gross_amount", "label": "Total", "fieldtype": "Currency","options":"Company:company:default_currency", "width": 150},
		]
