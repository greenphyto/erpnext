import frappe
from frappe.utils import flt

COMPANY = "Greenphyto Pte Ltd"
POSTING_DATE = "2026-09-17"
TARGET_ACCOUNT = "126000 - Stock - R&D Raw Materials - GPL"
REMARK = f"Move R&D raw material stock balance to {TARGET_ACCOUNT} as at {POSTING_DATE}"


def execute():
    validate_target_account()
    if frappe.db.exists("Journal Entry", {"company": COMPANY, "user_remark": REMARK, "docstatus": ["!=", 2]}):
        return

    account_values = get_account_values()
    if not account_values:
        return

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = POSTING_DATE
    je.company = COMPANY
    je.user_remark = REMARK
    cost_center = frappe.db.get_value("Company", COMPANY, "cost_center")
    for account, value in sorted(account_values.items()):
        value = flt(value, 2)
        if value > 0:
            debit_account, credit_account = TARGET_ACCOUNT, account
        else:
            debit_account, credit_account = account, TARGET_ACCOUNT
        amount = abs(value)
        je.append("accounts", {
            "account": debit_account,
            "debit": amount,
            "debit_in_account_currency": amount,
            "cost_center": cost_center,
            "user_remark": f"R&D stock balance: {value:.2f}",
        })
        je.append("accounts", {
            "account": credit_account,
            "credit": amount,
            "credit_in_account_currency": amount,
            "cost_center": cost_center,
            "user_remark": f"R&D stock balance: {value:.2f}",
        })

    je.insert()
    frappe.db.commit()
    total = flt(sum(abs(value) for value in account_values.values()), 2)
    frappe.msgprint(f"Journal Entry draft: {je.name}; accounts: {len(je.accounts)}; value: {total:.2f}")


def validate_target_account():
    account = frappe.db.get_value("Account", TARGET_ACCOUNT, ["company", "is_group"], as_dict=True)
    if not account or account.company != COMPANY or account.is_group:
        frappe.throw(f"Invalid target account: {TARGET_ACCOUNT}")


def get_account_values():
    from erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history import execute as run_report

    filters = frappe._dict({
        "from_date": POSTING_DATE,
        "to_date": POSTING_DATE,
        "item_group": "Raw Material",
    })
    _, rows = run_report(filters)
    item_codes = set(frappe.get_all("Item", filters={"item_group": "Raw Material", "rnd_item": 1}, pluck="name"))
    mappings = frappe.get_all(
        "Part Number Details",
        fields=["code", "account_code", "company"],
        filters={"code": ["in", list(item_codes)]},
    )
    accounts = {}
    for row in mappings:
        if row.company == COMPANY or row.code not in accounts:
            accounts[row.code] = row.account_code

    values = {}
    for row in rows:
        account = accounts.get(row[0])
        value = flt(row[13], 2)
        if account and account != TARGET_ACCOUNT and value:
            values[account] = flt(values.get(account, 0) + value, 2)
    return {account: value for account, value in values.items() if value}
