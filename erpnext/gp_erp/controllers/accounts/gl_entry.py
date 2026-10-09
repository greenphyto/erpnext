import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

import erpnext
from erpnext.accounts.doctype.gl_entry.gl_entry import GLEntry
from erpnext.accounts.utils import get_fiscal_year


class GLEntryGP(GLEntry):
    def validate(self):
        self.flags.ignore_submit_comment = True
        self.validate_and_set_fiscal_year()
        self.set_default_cost_center_value()
        self.pl_must_have_cost_center()
        if not self.flags.from_repost and self.voucher_type != "Period Closing Voucher":
            self.check_mandatory()
            self.validate_party()
            self.validate_currency()
        self.set_against_value()

    def set_against_value(self):
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

        acc_flags = "- " + frappe.get_value("Company", self.company, "abbr") or ""
        against_account = []
        against_party = []
        against_account_number = []
        for against in against_list:
            if acc_flags in against:
                account_name, account_number = frappe.db.get_value("Account", against, ["account_name", "account_number"]) or ["", 0]
                against_name = account_name + acc_flags
                if against_name:
                    against_account.append(against_name)
                if account_number:
                    against_account_number.append(account_number)
            else:
                if against:
                    against_party.append(against)
                accounts = frappe.db.get_all("GL Entry", {
                    "voucher_type": self.voucher_type,
                    "voucher_no": self.voucher_no,
                    "name": ['!=', self.name]
                }, "account")
                for acc in accounts:
                    account_name, account_number = frappe.db.get_value("Account", acc.account, ["account_name", "account_number"]) or ["", 0]
                    against_name = account_name + acc_flags
                    if against_name:
                        against_account.append(against_name)
                    if account_number:
                        against_account_number.append(account_number)

        self.against_account = ", ".join(list(set(against_account)))
        self.against_party = ", ".join(list(set(against_party)))
        self.against_account_number = ", ".join(list(set(against_account_number)))
        self.account_number = frappe.get_value("Account", self.account, "account_number")

    def set_default_cost_center_value(self):
        report_type = frappe.db.get_value("Account", self.account, "report_type")
        if report_type != "Profit and Loss":
            return
        if not self.cost_center:
            self.cost_center = erpnext.get_default_cost_center(company=self.company, account=self.account)
            return

    def check_mandatory(self):
        mandatory = ["account", "voucher_type", "voucher_no", "company"]
        for k in mandatory:
            if not self.get(k):
                frappe.throw(_("{0} is required to create a GL Entry").format(_(k.replace("_", " "))))
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
        if self.cost_center or self.voucher_type == "Period Closing Voucher" or allow_cost_center_missing(self):
            return
        if frappe.get_cached_value("Account", self.account, "report_type") == "Profit and Loss":
            if not self.cost_center:
                frappe.throw(
                    _("{0} {1}: Cost Center is required for PL account {2}").format(
                        self.voucher_type, self.voucher_no, frappe.bold(self.account)
                    )
                )


def get_comma_in_name_account():
    return [x.name for x in frappe.db.sql('select name from `tabAccount` where name like "%,%"', as_dict=1)]


def allow_cost_center_missing(gl):
    cur_fiscal_year = get_fiscal_year(nowdate(), as_dict=True)
    if getdate(gl.posting_date) < cur_fiscal_year.year_start_date:
        return True
    return False
