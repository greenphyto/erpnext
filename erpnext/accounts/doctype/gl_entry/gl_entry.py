# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.meta import get_field_precision
from frappe.model.naming import set_name_from_naming_options
from frappe.utils import flt, fmt_money

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)
from erpnext.accounts.doctype.accounting_dimension_filter.accounting_dimension_filter import (
	get_dimension_filter_map,
)
from erpnext.accounts.party import validate_party_frozen_disabled, validate_party_gle_currency
from erpnext.accounts.utils import get_account_currency, get_fiscal_year
from erpnext.exceptions import (
	InvalidAccountCurrency,
	InvalidAccountDimensionError,
	MandatoryAccountDimensionError,
)

exclude_from_linked_with = True


class GLEntry(Document):
	def autoname(self):
		"""
		Temporarily name doc for fast insertion
		name will be changed using autoname options (in a scheduled job)
		"""
		self.name = frappe.generate_hash(txt="", length=10)
		if self.meta.autoname == "hash":
			self.to_rename = 0

	def validate(self):
		self.flags.ignore_submit_comment = True
		self.validate_and_set_fiscal_year()
		self.pl_must_have_cost_center()

		if not self.flags.from_repost and self.voucher_type != "Period Closing Voucher":
			self.check_mandatory()
			self.validate_cost_center()
			self.check_pl_account()
			self.validate_party()
			self.validate_currency()

		self.set_against_value()

	def on_update(self):
		adv_adj = self.flags.adv_adj
		if not self.flags.from_repost and self.voucher_type != "Period Closing Voucher":
			self.validate_account_details(adv_adj)
			self.validate_dimensions_for_pl_and_bs()
			self.validate_allowed_dimensions()
			validate_balance_type(self.account, adv_adj)
			validate_frozen_account(self.account, adv_adj)

			if frappe.db.get_value("Account", self.account, "account_type") not in [
				"Receivable",
				"Payable",
			]:
				# Update outstanding amt on against voucher
				if (
					self.against_voucher_type in ["Journal Entry", "Sales Invoice", "Purchase Invoice", "Fees"]
					and self.against_voucher
					and self.flags.update_outstanding == "Yes"
					and not frappe.flags.is_reverse_depr_entry
				):
					update_outstanding_amt(
						self.account, self.party_type, self.party, self.against_voucher_type, self.against_voucher
					)

	def set_against_value(self):
		# sometime against has multiple value like "account1, account2, account3"
		# so, we need to split by comma
		# but also, sometimes account name has comma inside the text, it will be like "IT, Internet, Wifi - GPL" 
		# and it will conflict if joined like "account1, account2, account3, IT, Internet, Wifi - GPL"
		# so we sill need temporary converting this comma in text become another character, and convert back after split

		if not self.against:
			return
		
		if self.against_party:
			self.against_account = self.against

		if "," in self.against:
			comma_account = get_comma_in_name_account()

			against_value = self.against
			do_convert = False
			for acc in comma_account:
				if acc in against_value:
					new_name = acc.replace(",", "%2C")
					against_value = against_value.replace(acc, new_name)
					do_convert = True
			
			against_list = [x.strip() for x in against_value.split(",")]
			if do_convert:
				for i, value in enumerate(against_list):
					if "%2C" in value:
						against_list[i] = value.replace("%2C", ",")
		else:
			against_list = [self.against]


		acc_flags = "- "+frappe.get_value("Company", self.company, "abbr") or ""
		
		against_account = []
		against_party = []
		against_account_number = []
		for against in against_list:
			if acc_flags in against:
				account_name, account_number  = frappe.db.get_value("Account", against, ["account_name", "account_number"]) or ["", 0]
				against  = account_name + acc_flags
				if against:
					against_account.append(against)
				if account_number:
					against_account_number.append(account_number)
			else:
				if against:
					against_account.append(against)
					against_party.append(against)

		self.against_account = ", ".join(against_account)
		self.against_party =  ", ".join(against_party)
		self.against_account_number = ", ".join(against_account_number)
		self.account_number = frappe.get_value("Account", self.account, "account_number")

	def check_mandatory(self):
	 
		mandatory = ["account", "voucher_type", "voucher_no", "company"]
		for k in mandatory:
			if not self.get(k):
				frappe.throw(_("{0} is required").format(_(self.meta.get_label(k))))

		if not (self.party_type and self.party):
			account_type = frappe.get_cached_value("Account", self.account, "account_type")
			if account_type == "Receivable":
				frappe.throw(
					_("{0} {1}: Customer is required against Receivable account {2} When making GL Entry.").format(
						self.voucher_type, self.voucher_no, self.account
					)
				)
			elif account_type == "Payable":
				frappe.throw(
					_("{0} {1}: Supplier is required against Payable account {2} When making GL Entry.").format(
						self.voucher_type, self.voucher_no, self.account
					)
				)

		# Zero value transaction is not allowed
		if not (
			flt(self.debit, self.precision("debit"))
			or flt(self.credit, self.precision("credit"))
			or (
				self.voucher_type == "Journal Entry"
				and frappe.get_cached_value("Journal Entry", self.voucher_no, "voucher_type")
				== "Exchange Gain Or Loss"
			)
		):
			frappe.throw(
				_("{0} {1}: Either debit or credit amount is required for {2}").format(
					self.voucher_type, self.voucher_no, self.account
				)
			)

	def pl_must_have_cost_center(self):
		"""Validate that profit and loss type account GL entries have a cost center."""

		if self.cost_center or self.voucher_type == "Period Closing Voucher":
			return

		if frappe.get_cached_value("Account", self.account, "report_type") == "Profit and Loss":
			msg = _("{0} {1}: Cost Center is required for 'Profit and Loss' account {2}.").format(
				self.voucher_type, self.voucher_no, self.account
			)
			msg += " "
			msg += _(
				"Please set the cost center field in {0} or setup a default Cost Center for the Company."
			).format(self.voucher_type)

			frappe.throw(msg, title=_("Missing Cost Center"))

	def validate_dimensions_for_pl_and_bs(self):
		account_type = frappe.db.get_value("Account", self.account, "report_type")

		for dimension in get_checks_for_pl_and_bs_accounts():
			if (
				account_type == "Profit and Loss"
				and self.company == dimension.company
				and dimension.mandatory_for_pl
				and not dimension.disabled
			):
				if not self.get(dimension.fieldname):
					frappe.throw(
						_("Accounting Dimension <b>{0}</b> is required for 'Profit and Loss' account {1}.").format(
							dimension.label, self.account
						)
					)

			if (
				account_type == "Balance Sheet"
				and self.company == dimension.company
				and dimension.mandatory_for_bs
				and not dimension.disabled
			):
				if not self.get(dimension.fieldname):
					frappe.throw(
						_("Accounting Dimension <b>{0}</b> is required for 'Balance Sheet' account {1}.").format(
							dimension.label, self.account
						)
					)

	def validate_allowed_dimensions(self):
		dimension_filter_map = get_dimension_filter_map()
		for key, value in dimension_filter_map.items():
			dimension = key[0]
			account = key[1]

			if self.account == account:
				if value["is_mandatory"] and not self.get(dimension):
					frappe.throw(
						_("{0} is mandatory for account {1}").format(
							frappe.bold(frappe.unscrub(dimension)), frappe.bold(self.account)
						),
						MandatoryAccountDimensionError,
					)

				if value["allow_or_restrict"] == "Allow":
					if self.get(dimension) and self.get(dimension) not in value["allowed_dimensions"]:
						frappe.throw(
							_("Invalid value {0} for {1} against account {2}").format(
								frappe.bold(self.get(dimension)),
								frappe.bold(frappe.unscrub(dimension)),
								frappe.bold(self.account),
							),
							InvalidAccountDimensionError,
						)
				else:
					if self.get(dimension) and self.get(dimension) in value["allowed_dimensions"]:
						frappe.throw(
							_("Invalid value {0} for {1} against account {2}").format(
								frappe.bold(self.get(dimension)),
								frappe.bold(frappe.unscrub(dimension)),
								frappe.bold(self.account),
							),
							InvalidAccountDimensionError,
						)

	def check_pl_account(self):
		if (
			self.is_opening == "Yes"
			and frappe.db.get_value("Account", self.account, "report_type") == "Profit and Loss"
			and not self.is_cancelled
		):
			frappe.throw(
				_("{0} {1}: 'Profit and Loss' type account {2} not allowed in Opening Entry").format(
					self.voucher_type, self.voucher_no, self.account
				)
			)

	def validate_account_details(self, adv_adj):
		"""Account must be ledger, active and not freezed"""

		ret = frappe.db.sql(
			"""select is_group, docstatus, company
			from tabAccount where name=%s""",
			self.account,
			as_dict=1,
		)[0]

		if ret.is_group == 1:
			frappe.throw(
				_(
					"""{0} {1}: Account {2} is a Group Account and group accounts cannot be used in transactions"""
				).format(self.voucher_type, self.voucher_no, self.account)
			)

		if ret.docstatus == 2:
			frappe.throw(
				_("{0} {1}: Account {2} is inactive").format(self.voucher_type, self.voucher_no, self.account)
			)

		if ret.company != self.company:
			frappe.throw(
				_("{0} {1}: Account {2} does not belong to Company {3}").format(
					self.voucher_type, self.voucher_no, self.account, self.company
				)
			)

	def validate_cost_center(self):
		if not self.cost_center:
			return

		is_group, company = frappe.get_cached_value(
			"Cost Center", self.cost_center, ["is_group", "company"]
		)

		if company != self.company:
			frappe.throw(
				_("{0} {1}: Cost Center {2} does not belong to Company {3}").format(
					self.voucher_type, self.voucher_no, self.cost_center, self.company
				)
			)

		if self.voucher_type != "Period Closing Voucher" and is_group:
			frappe.throw(
				_(
					"""{0} {1}: Cost Center {2} is a group cost center and group cost centers cannot be used in transactions"""
				).format(self.voucher_type, self.voucher_no, frappe.bold(self.cost_center))
			)

	def validate_party(self):
		validate_party_frozen_disabled(self.party_type, self.party)

	def validate_currency(self):
		company_currency = erpnext.get_company_currency(self.company)
		account_currency = get_account_currency(self.account)

		if not self.account_currency:
			self.account_currency = account_currency or company_currency

		if account_currency != self.account_currency:
			frappe.throw(
				_("{0} {1}: Accounting Entry for {2} can only be made in currency: {3}").format(
					self.voucher_type, self.voucher_no, self.account, (account_currency or company_currency)
				),
				InvalidAccountCurrency,
			)

		if self.party_type and self.party:
			validate_party_gle_currency(self.party_type, self.party, self.company, self.account_currency)

	def validate_and_set_fiscal_year(self):
		if not self.fiscal_year:
			self.fiscal_year = get_fiscal_year(self.posting_date, company=self.company)[0]

	def on_cancel(self):
		msg = _("Individual GL Entry cannot be cancelled.")
		msg += "<br>" + _("Please cancel related transaction.")
		frappe.throw(msg)


def validate_balance_type(account, adv_adj=False):
	if not adv_adj and account:
		balance_must_be = frappe.db.get_value("Account", account, "balance_must_be")
		if balance_must_be:
			balance = frappe.db.sql(
				"""select sum(debit) - sum(credit)
				from `tabGL Entry` where account = %s""",
				account,
			)[0][0]

			if (balance_must_be == "Debit" and flt(balance) < 0) or (
				balance_must_be == "Credit" and flt(balance) > 0
			):
				frappe.throw(
					_("Balance for Account {0} must always be {1}").format(account, _(balance_must_be))
				)


def update_outstanding_amt(
	account, party_type, party, against_voucher_type, against_voucher, on_cancel=False
):
	if party_type and party:
		party_condition = " and party_type={0} and party={1}".format(
			frappe.db.escape(party_type), frappe.db.escape(party)
		)
	else:
		party_condition = ""

	if against_voucher_type == "Sales Invoice":
		party_account = frappe.db.get_value(against_voucher_type, against_voucher, "debit_to")
		account_condition = "and account in ({0}, {1})".format(
			frappe.db.escape(account), frappe.db.escape(party_account)
		)
	else:
		account_condition = " and account = {0}".format(frappe.db.escape(account))

	# get final outstanding amt
	bal = flt(
		frappe.db.sql(
			"""
		select sum(debit_in_account_currency) - sum(credit_in_account_currency)
		from `tabGL Entry`
		where against_voucher_type=%s and against_voucher=%s
		and voucher_type != 'Invoice Discounting'
		{0} {1}""".format(
				party_condition, account_condition
			),
			(against_voucher_type, against_voucher),
		)[0][0]
		or 0.0
	)

	if against_voucher_type == "Purchase Invoice":
		bal = -bal
	elif against_voucher_type == "Journal Entry":
		against_voucher_amount = flt(
			frappe.db.sql(
				"""
			select sum(debit_in_account_currency) - sum(credit_in_account_currency)
			from `tabGL Entry` where voucher_type = 'Journal Entry' and voucher_no = %s
			and account = %s and (against_voucher is null or against_voucher='') {0}""".format(
					party_condition
				),
				(against_voucher, account),
			)[0][0]
		)

		if not against_voucher_amount:
			frappe.throw(
				_("Against Journal Entry {0} is already adjusted against some other voucher").format(
					against_voucher
				)
			)

		bal = against_voucher_amount + bal
		if against_voucher_amount < 0:
			bal = -bal

		# Validation : Outstanding can not be negative for JV
		if bal < 0 and not on_cancel:
			frappe.throw(
				_("Outstanding for {0} cannot be less than zero ({1})").format(against_voucher, fmt_money(bal))
			)

	if against_voucher_type in ["Sales Invoice", "Purchase Invoice", "Fees"]:
		ref_doc = frappe.get_doc(against_voucher_type, against_voucher)

		# Didn't use db_set for optimization purpose
		ref_doc.outstanding_amount = bal
		frappe.db.set_value(against_voucher_type, against_voucher, "outstanding_amount", bal)

		ref_doc.set_status(update=True)


def validate_frozen_account(account, adv_adj=None):
	frozen_account = frappe.get_cached_value("Account", account, "freeze_account")
	if frozen_account == "Yes" and not adv_adj:
		frozen_accounts_modifier = frappe.db.get_value(
			"Accounts Settings", None, "frozen_accounts_modifier"
		)

		if not frozen_accounts_modifier:
			frappe.throw(_("Account {0} is frozen").format(account))
		elif frozen_accounts_modifier not in frappe.get_roles():
			frappe.throw(_("Not authorized to edit frozen Account {0}").format(account))


def update_against_account(voucher_type, voucher_no):
	entries = frappe.db.get_all(
		"GL Entry",
		filters={"voucher_type": voucher_type, "voucher_no": voucher_no},
		fields=["name", "party", "against", "debit", "credit", "account", "company"],
	)

	if not entries:
		return
	company_currency = erpnext.get_company_currency(entries[0].company)
	precision = get_field_precision(frappe.get_meta("GL Entry").get_field("debit"), company_currency)

	accounts_debited, accounts_credited = [], []
	for d in entries:
		if flt(d.debit, precision) > 0:
			accounts_debited.append(d.party or d.account)
		if flt(d.credit, precision) > 0:
			accounts_credited.append(d.party or d.account)

	for d in entries:
		if flt(d.debit, precision) > 0:
			new_against = ", ".join(list(set(accounts_credited)))
		if flt(d.credit, precision) > 0:
			new_against = ", ".join(list(set(accounts_debited)))

		if d.against != new_against:
			frappe.db.set_value("GL Entry", d.name, "against", new_against)


def on_doctype_update():
	frappe.db.add_index("GL Entry", ["against_voucher_type", "against_voucher"])
	frappe.db.add_index("GL Entry", ["voucher_type", "voucher_no"])


def rename_gle_sle_docs():
	for doctype in ["GL Entry", "Stock Ledger Entry"]:
		rename_temporarily_named_docs(doctype)


def rename_temporarily_named_docs(doctype):
	"""Rename temporarily named docs using autoname options"""
	docs_to_rename = frappe.get_all(doctype, {"to_rename": "1"}, order_by="creation", limit=50000)
	for doc in docs_to_rename:
		oldname = doc.name
		set_name_from_naming_options(frappe.get_meta(doctype).autoname, doc)
		newname = doc.name
		frappe.db.sql(
			"UPDATE `tab{}` SET name = %s, to_rename = 0 where name = %s".format(doctype),
			(newname, oldname),
			auto_commit=True,
		)


def rename_old_against_account_gl_entry():
	acc_map = mapping_previous_merge_account()
	ledger_map = mapping_previous_merge_ledger()
	manual_map = get_manual_map()

	data1 = frappe.db.sql("""
		SELECT 
			against_account, posting_date, g.name AS gl_name, a.name, "account" as types
		FROM
			`tabGL Entry` g
				LEFT JOIN
			`tabAccount` a ON a.name LIKE against_account
		WHERE
			against_account NOT REGEXP '^[0-9]{5}'
				AND against_account IS NOT NULL
				AND a.name IS NULL
				and against_account != ""
		group by g.name
	limit 99999
	""", as_dict=1)

	data2 = frappe.db.sql("""
		SELECT 
			against, against_party, posting_date, g.name AS gl_name, a.name, "party" as types
		FROM
			`tabGL Entry` g
				LEFT JOIN
			`tabAccount` a ON a.name LIKE against_party
		WHERE
			against_party NOT REGEXP '^[0-9]{5}'
				AND against_party IS NOT NULL
				AND a.name IS NULL
				and against_party != ""
				and against_party like "%GPL%"
		group by g.name
		order by against_party desc
	limit 99999
	""", as_dict=1)

	data = data1 + data2

	for i,d in enumerate(data):
		text = d.get("against") or d.get("against_account")
		text = text.replace("GPL,", "GPL|")
		text = text.replace("), ", ")|")
		if d.get("types") == "party":
			text = text.replace(",", "|")
		accounts = [x.strip() for x in text.split('|')]
		acc_list = []
		party_list = []
		print(accounts)
		for acc in accounts:
			new_name = manual_map.get(acc) or acc_map.get(acc) or ledger_map.get(acc)
			print(acc_map.get(acc), ledger_map.get(acc), acc)
			if new_name:
				acc_list.append(new_name)
			else:
				party_list.append(acc)
		
		print("ACC  ", acc_list)
		print("PARTY", party_list)
		new_against_account = ", ".join(acc_list) 
		new_against_party = ", ".join(party_list)
		frappe.db.set_value("GL Entry", d.gl_name, "against_account", new_against_account) 
		frappe.db.set_value("GL Entry", d.gl_name, "against_party", new_against_party) 
		print("Update", d.gl_name)
		print("\n")

def mapping_previous_merge_account():
	map = {}
	data = frappe.db.sql("""
		SELECT 
			a.name, c.content, c.creation
		FROM
			`tabAccount` a
				LEFT JOIN
			`tabComment` c ON c.reference_name = a.name and c.comment_type = 'Edit'
		order by c.creation asc
	""", as_dict=1)
	for d in data:
		content = d.content
		if content:
			text = content.replace("<strong>", "|")
			text = text.replace("</strong>", "|")
			text = text.replace("&amp;", "&")
			accounts = text.split("|")
			# print(accounts)
			from_name = accounts[1]
			to_name = accounts[3]
			map[from_name] = to_name
	
	return map

def mapping_previous_merge_ledger():
	map = {}
	data = frappe.db.sql("""
	SELECT 
		account, creation, account_name
	FROM
		`tabLedger Merge Accounts`
	order by creation asc
	""", as_dict=1)
	for d in data:
		map[d.account_name] = d.account
	
	return map

def get_manual_map():
	map = {
		"GST Input Tax (Purchases) - GPL":"147000 - GST Input Tax - GPL",
		"Retained Earnings - GPL": "340000 - Retained Earnings - GPL",
		"Bank DBS 003-9282-010 - GPL":"161023 - DBS - SGD - 003-928-2010 - GPL",
		"Bank UOB SGD 348-323-621-0 - GPL":"161027 - UOB - SGD (Main) - GPL",
		"CPF - GPL":"620200 - CPF - GPL",
		"Salary-Executive - GPL":"620000 - Salary - GPL",
		"SDL - GPL":"621400 - SDL Fund - GPL",
		"Fixtures - GPL":"110050 - Furniture & Fittings - GPL"
	}

	return map

def get_comma_in_name_account():
	return [x.name for x in frappe.db.sql('select name from `tabAccount` where name like "%,%"', as_dict=1)]

def fix_against_account_in_party_gl():
	data = frappe.db.sql("""
		SELECT 
			against, name, against_account, against_party, voucher_no, voucher_type, party
		FROM
			`tabGL Entry`
		WHERE
			
			(against_account = "" or against_account is NULL)
		ORDER BY voucher_type asc;
	""", as_dict=1)

	account_map = {}

	total_count = len(data)

	for i,d in enumerate(data):
		cdt = d.voucher_type
		cdn = d.voucher_no
		key = (cdn, d.against_party)
		account = account_map.get(key)
		progress = flt(i/total_count*100)
		print("loop", flt(progress, 2), cdt, cdn, d.against_party)
		if not account:
			if cdt == "Sales Invoice":
				account = frappe.db.get_value(cdt, cdn, "debit_to")
			elif cdt == "Purchase Invoice":
				account = frappe.db.get_value(cdt, cdn, "credit_to")
			elif cdt == "Payment Entry":
				paid_to, paid_from, types = frappe.db.get_value(cdt, cdn, ['paid_to', 'paid_from', 'payment_type']) or ("", "", "")
				if types == "Receive":
					account = paid_from
				else:
					account = paid_to
		
			elif cdt == "Journal Entry":
				acc = []
				doc = frappe.get_doc(cdt, cdn)
				party = d.against_party or d.against or d.party
				for x in doc.get("accounts"):
					if x.party and x.party in party and x.account not in acc:
						acc.append(x.account)
				
				account = ", ".join(acc)
	
		if account:
			print("Update", d.name, account)
			print()

			frappe.db.set_value("GL Entry", d.name, "against_account", account)
				

def fix_against_party_in_gl():
	data = frappe.db.sql("""
		update
			`tabGL Entry`
		set against_party = against
		WHERE
			against_party IN (NULL , '')
				AND against IS NOT NULL
				and against not like "%GPL%"
	""", as_dict=1)


def remove_account_number():
	data = frappe.db.sql("select name, against_account from `tabGL Entry` where against_account is not null limit 99999", as_dict=1)
	account = frappe.db.sql("select name, account_name from `tabAccount`", as_dict=1)
	account_map = {}
	for d in account:
		account_map[d.name] = d.account_name + " - GPL"

	idx = 0
	print(len(data))
	for d in data:
		dt = d.against_account.replace("GPL, ", "GPL|`|")
		dt = dt.split("|`|")
		idx+=1
		res = []
		for x in dt:
			new_name = account_map.get(x) or x
			if new_name not in res:
				res.append(new_name)
		
		new_value = ", ".join(res)
		frappe.db.set_value("GL Entry", d.name, "against_account", new_value)
		if idx & 100 == 0:
			print("Index",idx, dt, new_value)
			frappe.db.commit()
		
def add_account_number():
	data = frappe.db.sql("select name, against_account from `tabGL Entry` where against_account is not null limit 99999", as_dict=1)
	account = frappe.db.sql("select name, account_name, account_number from `tabAccount`", as_dict=1)
	account_map = {}
	for d in account:
		key = f"{d.account_name} - GPL"
		account_map[key] = d.account_number

	idx = 0
	print(len(data))
	for d in data:
		dt = d.against_account.replace("GPL, ", "GPL|`|")
		dt = dt.split("|`|")
		idx+=1
		res = []
		for x in dt:
			new_name = account_map.get(x)
			if new_name and new_name not in res:
				res.append(new_name)
		
		new_value = ", ".join(res)
		frappe.db.set_value("GL Entry", d.name, "against_account_number", new_value)

		if idx & 100 == 0:
			print("Index",idx, dt, new_value)
			frappe.db.commit()

def regrenerate_against_account():
	# find missing against account
	data = frappe.db.sql("""
		SELECT 
			against, name, against_account, against_party, voucher_no, voucher_type, party, debit, credit, debit_in_account_currency, credit_in_account_currency
		FROM
			`tabGL Entry`
		WHERE
			voucher_type != "Period Closing Voucher" and
			((against_account = "" or against_account is NULL) or (against_account_number = "" or against_account_number is NULL))
		ORDER BY voucher_type asc limit 99999;
	""", as_dict=1)


	for i,d in enumerate(data):
		cdt = d.voucher_type
		cdn = d.voucher_no
		find_debit=False
		print("Working on ", cdt, cdn, d.name)

		dt = []
		debit = d.debit or d.debit_in_account_currency
		credit = d.credit or d.credit_in_account_currency
		if flt(debit) > 0:
			dt = frappe.db.sql("select account, party from`tabGL Entry` where (credit > 0 or credit_in_account_currency > 0) and voucher_type = %s and voucher_no = %s", (cdt, cdn), as_dict=1)
		if flt(credit) > 0:
			dt = frappe.db.sql("select account, party from`tabGL Entry` where (debit > 0 or debit_in_account_currency > 0) and voucher_type = %s and voucher_no = %s", (cdt, cdn), as_dict=1)
		ags = []
		ags_num = []
		for x in dt:
			temp = frappe.get_value("Account", x.account, ["account_name", "account_number"], as_dict=1)
			against_name, against_number = temp.account_name + " - GPL", temp.account_number
			ags.append(against_name)
			ags_num.append(against_number)
		
		if ags:
			res = ", ".join(ags)
			frappe.db.set_value("GL Entry", d.name, "against_account", res)
		if ags_num:
			res = ", ".join(ags_num)
			frappe.db.set_value("GL Entry", d.name, "against_account_number", res)

		if i % 100 == 0:
			frappe.db.commit()


	