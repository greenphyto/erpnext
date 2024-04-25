import frappe

def fix_shenzen():
    print("Fix Shenzen")
    # PLE
    frappe.db.set_value("Payment Ledger Entry", "adaab9bf2e", "against_voucher_type", "Purchase Invoice")
    frappe.db.set_value("Payment Ledger Entry", "adaab9bf2e", "against_voucher_no", "PI00477/2024-1")
    # PI
    # this hardcoded to paid and remove the left outstanding (CNY 235.13)
    frappe.db.set_value("Purchase Invoice", "PI00477/2024-1", "status", "Paid")
    frappe.db.set_value("Purchase Invoice", "PI00477/2024-1", "outstanding_amount", 0)

def fix_yusran_jv():
    print("Fix Yusran")
    # JV
    frappe.db.set_value("Journal Entry Account", "1c3a9c827f", "reference_name", "ACC-JV-2022-00092")
    frappe.db.set_value("Journal Entry Account", "1c3a9c827f", "reference_type", "Journal Entry")

    # GL
    frappe.db.set_value("GL Entry", "ACC-GLE-2022-02429", "against_voucher_type", "Journal Entry")
    frappe.db.set_value("GL Entry", "ACC-GLE-2022-02429", "against_voucher", "ACC-JV-2022-00092")

    # PLE
    frappe.db.set_value("Payment Ledger Entry", "b06329cb05", "against_voucher_type", "Journal Entry")
    frappe.db.set_value("Payment Ledger Entry", "b06329cb05", "against_voucher_no", "ACC-JV-2022-00092")

def fix_greenpac():
    print("Fix Greenpac")
    # GL
    frappe.db.set_value("GL Entry", "ACC-GLE-2022-01073", "against_voucher", "PI266/10/2022")
    # PLE
    frappe.db.set_value("Payment Ledger Entry", "90a5c06d9f", "against_voucher_type", "Purchase Invoice")
    frappe.db.set_value("Payment Ledger Entry", "90a5c06d9f", "against_voucher_no", "PI266/10/2022")
    # PE
    frappe.db.set_value("Payment Entry Reference", "b5c9006824", "reference_name", "PI266/10/2022")
    # PI
    frappe.db.set_value("Purchase Invoice", "PI266/10/2022", "status", "Paid")
    frappe.db.set_value("Purchase Invoice", "PI266/10/2022", "outstanding_amount", 0)


def fix_pauline():
    print("Fix Pauline")
    # GL
    frappe.db.set_value("GL Entry", "ACC-GLE-2022-00414", "against_voucher_type", "Sales Invoice")
    frappe.db.set_value("GL Entry", "ACC-GLE-2022-00414", "against_voucher", "INV006/12/2021")
    # PLE
    frappe.db.set_value("Payment Ledger Entry", "397d4b1d70", "against_voucher_type", "Sales Invoice")
    frappe.db.set_value("Payment Ledger Entry", "397d4b1d70", "against_voucher_no", "INV006/12/2021")
    # SI
    frappe.db.set_value("Sales Invoice", "INV006/12/2021", "status", "Paid")
    frappe.db.set_value("Sales Invoice", "INV006/12/2021", "outstanding_amount", 0)

"""
bench --site test3 execute erpnext.patches.v14_0.repair_trade_transaction.execute
"""
def execute():
    fix_pauline()
    fix_yusran_jv()
    fix_greenpac()