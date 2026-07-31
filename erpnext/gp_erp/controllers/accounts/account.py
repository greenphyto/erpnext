import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import get_descendants_of

from erpnext.accounts.doctype.account.account import Account


class AccountGP(Account):
    def on_update(self):
        super(AccountGP, self).on_update()
        self.sync_child_accounts()

    def sync_child_accounts(self):
        descendants = get_descendants_of("Company", self.company, ignore_permissions=True)
        if not descendants:
            return
        parent_acc_name_map = {}
        for company in descendants:
            parent_acc_name_map[company] = frappe.db.get_value(
                "Account",
                {"account_name": self.account_name, "company": company},
                "name",
            )
            if not parent_acc_name_map[company]:
                doc = frappe.new_doc("Account")
                doc.update(
                    {
                        "account_name": self.account_name,
                        "company": company,
                        "parent_account": parent_acc_name_map[company],
                    }
                )
                doc.flags.ignore_permissions = True
                doc.save()
                frappe.msgprint(_("Account {0} is added in the child company {1}").format(doc.name, company))
            elif parent_acc_name_map[company]:
                doc = frappe.get_doc("Account", parent_acc_name_map[company])
                parent_value_changed = False
                for field in ["account_type", "freeze_account", "balance_must_be", "is_trade_related"]:
                    if doc.get(field) != self.get(field):
                        parent_value_changed = True
                        doc.set(field, self.get(field))
                if parent_value_changed:
                    doc.flags.ignore_permissions = True
                    doc.save()
