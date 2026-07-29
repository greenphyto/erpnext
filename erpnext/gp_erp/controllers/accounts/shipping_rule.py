import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.doctype.shipping_rule.shipping_rule import ShippingRule


class ShippingRuleGP(ShippingRule):
    def calculate_shipping_amount(self, app_args):
        if not self.shipping_amount:
            return
        return super(ShippingRuleGP, self).calculate_shipping_amount(app_args)
