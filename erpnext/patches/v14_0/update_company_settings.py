import frappe

def execute():
    # add WIP account
    add_wip_account()
    add_cost_center()
    _update_company_settings()

def _update_company_settings():
    print("Update Company Settings for manufacturing section")
    doc = frappe.get_doc("Company", "Greenphyto Pte Ltd")
    doc.default_cost_expense_account = "540000 - COS Prod Variance - GPL"
    doc.cost_center_for_production = "2020 - Production-WH - GPL"
    doc.cost_center_for_packing = "4020 - Packing - GPL"

    if not doc.operation_wip_account:
        data = [
            ("Seeding", "121301 - Stock - Seeding WIP - GPL"),
            ("Transplanting", "121302 - Stock - Transplanting WIP - GPL"),
            ("Harvesting", "121303 - Stock - Harvesting WIP - GPL")
        ]
        for d in data:
            row = doc.append("operation_wip_account")
            row.operation = d[0]
            row.wip_account = d[1]
    
    doc.save()


def add_wip_account():
    # seeding
    accounts = [
        {
            "account_name": "Stock - Seeding WIP",
            "account_number": "121301",
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
        },
        {
            "account_name": "COS Prod Variance",
            "account_number": "540000",
            "is_group": 0,
            "company": "Greenphyto Pte Ltd",
            "root_type": "Expense",
            "report_type": "Profit and Loss",
            "account_currency": "SGD",
            "inter_company_account": 0,
            "parent_account": "Cost of Sales - GPL",
            "account_type": "",
            "tax_rate": 0,
            "is_trade_related": 0,
            "freeze_account": "No",
            "balance_must_be": "",
            "old_parent": "Cost of Sales - GPL",
            "include_in_gross": 0,
            "doctype":"Account"
        }
    ]

    for acc in accounts:
        if not frappe.db.get_value("Account", {"account_name": acc['account_name']} ):
            print("Creating new Account", acc['account_name'])
            doc = frappe.get_doc(acc)
            doc.insert()

def add_cost_center():
    costs = [
        {
            "cost_center_name": "Production-WH",
            "cost_center_number": "2020",
            "parent_cost_center": "GPL 10 - GPL",
            "company": "Greenphyto Pte Ltd",
            "is_group": 0,
            "disabled": 0,
            "old_parent": "GPL 10 - GPL",
            "doctype": "Cost Center",
        },
        {
            "cost_center_name": "Packing",
            "cost_center_number": "4020",
            "parent_cost_center": "GPL 10 - GPL",
            "company": "Greenphyto Pte Ltd",
            "is_group": 0,
            "disabled": 0,
            "old_parent": "GPL 10 - GPL",
            "doctype": "Cost Center"
        }
    ]

    for d in costs:
        if not frappe.db.get_value("Cost Center", {"cost_center_name": d['cost_center_name']} ):
            print("Creating new Cost Center", d['cost_center_name'])
            doc = frappe.get_doc(d)
            doc.insert()