import frappe

def execute():
    add_account()
    update_stock_settings()

def update_stock_settings():
    frappe.db.set_value("Stock Settings", "Stock Settings", "account_for_raw_material_scrap", "520900 - COS Material Scrapped - GPL")
    frappe.db.set_value("Stock Settings", "Stock Settings", "account_for_product_scrap", "500200 - COGS - Waste - GPL")

def add_account():
    # seeding
    accounts = [
        {
            "account_name": "COGS - Waste",
            "account_number": "500200",
            "is_group": 0,
            "company": "Greenphyto Pte Ltd",
            "root_type": "Expense",
            "report_type": "Profit and Loss",
            "account_currency": "SGD",
            "inter_company_account": 0,
            "parent_account": "Cost of Goods Sold - GPL",
            "account_type": "",
            "tax_rate": 0,
            "is_trade_related": 0,
            "freeze_account": "No",
            "balance_must_be": "",
            "old_parent": "Cost of Goods Sold - GPL",
            "include_in_gross": 0,
            "doctype": "Account",
        },
        {
            
            "account_name": "COS Material Scrapped",
            "account_number": "520900",
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
            "doctype": "Account",
        }
    ]


    for acc in accounts:
        if not frappe.db.exists("Account", {"account_name": acc['account_name']} ):
            print("Creating new Account", acc['account_name'])
            doc = frappe.get_doc(acc)
            doc.save()