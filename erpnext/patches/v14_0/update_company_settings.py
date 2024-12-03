import frappe

def execute():
    # add WIP account
    add_wip_account()

def add_wip_account():
    # seeding
    accounts = [
        {
            "account_name": "Stock - Seedingd WIP",
            "account_number": "121305",
            "is_group": 0,
            "company": "Greenphyto Pte Ltd",
            "root_type": "Asset",
            "report_type": "Balance Sheet",
            "account_currency": "SGD",
            "inter_company_account": 0,
            "parent_account": "100050 - Stock - GPL",
            "account_type": "",
            "tax_rate": 0,
            "is_trade_related": 0,
            "freeze_account": "No",
            "balance_must_be": "",
            "old_parent": "100050 - Stock - GPL",
            "include_in_gross": 0,
            "doctype":"Account"
        },
        {
            "account_name": "Stock - Transplanting WIP",
            "account_number": "121302",
            "is_group": 0,
            "company": "Greenphyto Pte Ltd",
            "root_type": "Asset",
            "report_type": "Balance Sheet",
            "account_currency": "SGD",
            "inter_company_account": 0,
            "parent_account": "100050 - Stock - GPL",
            "account_type": "",
            "tax_rate": 0,
            "is_trade_related": 0,
            "freeze_account": "No",
            "balance_must_be": "",
            "old_parent": "100050 - Stock - GPL",
            "include_in_gross": 0,
            "doctype":"Account"
        },
        {
            "account_name": "Stock - Harvesting WIP",
            "account_number": "121303",
            "is_group": 0,
            "company": "Greenphyto Pte Ltd",
            "root_type": "Asset",
            "report_type": "Balance Sheet",
            "account_currency": "SGD",
            "inter_company_account": 0,
            "parent_account": "100050 - Stock - GPL",
            "account_type": "",
            "tax_rate": 0,
            "is_trade_related": 0,
            "freeze_account": "No",
            "balance_must_be": "",
            "old_parent": "100050 - Stock - GPL",
            "include_in_gross": 0,
            "doctype":"Account"
        }
    ]

    for acc in accounts:
        if not frappe.db.get_value("Account", {"account_name": acc['account_name']} ):
            print("Creating new Account", acc['account_name'])
            doc = frappe.get_doc(acc)
            doc.insert()
