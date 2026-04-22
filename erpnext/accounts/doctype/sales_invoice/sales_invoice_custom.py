from .sales_invoice import SalesInvoice
import frappe

#Important!: always use super() to overide standard function

class SalesInvoiceCustom(SalesInvoice):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def validate(self):
        super().validate()
        frappe.msgprint("Custom validation logic executed")
