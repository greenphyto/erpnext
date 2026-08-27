import frappe
from frappe.utils import flt


FROM_DATE = "2026-06-01"
TO_DATE = "2026-08-15"


COMPANY = "Greenphyto Pte Ltd"
POSTING_DATE = "2026-08-15"


def execute():
    rows = get_report_rows()
    expense_account = frappe.db.get_value("Company", COMPANY, "stock_adjustment_account")
    cost_center = frappe.db.get_value("Company", COMPANY, "cost_center")

    account_diffs = {}
    account_items = {}
    for row in rows:
        account = row["account"]
        difference = row["difference"]
        if not account or not difference:
            continue
        account_diffs[account] = account_diffs.get(account, 0) + difference
        account_items.setdefault(account, []).append(f"{row['item_code']} ({difference:+.2f})")

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = POSTING_DATE
    je.company = COMPANY
    je.user_remark = f"Stock balance value correction as at {POSTING_DATE}"

    total_debit = 0
    total_credit = 0
    for account, difference in sorted(account_diffs.items()):
        difference = flt(difference, 2)
        if not difference:
            continue
        account_row = {
            "account": account,
            "cost_center": cost_center,
            "user_remark": ", ".join(account_items[account]),
        }
        if difference > 0:
            account_row.update({"debit": difference, "debit_in_account_currency": difference})
            total_debit += difference
        else:
            amount = abs(difference)
            account_row.update({"credit": amount, "credit_in_account_currency": amount})
            total_credit += amount
        je.append("accounts", account_row)

    balancing_amount = flt(abs(total_debit - total_credit), 2)
    if balancing_amount:
        account_row = {
            "account": expense_account,
            "cost_center": cost_center,
            "user_remark": "Balancing entry",
        }
        if total_debit > total_credit:
            account_row.update({"credit": balancing_amount, "credit_in_account_currency": balancing_amount})
        else:
            account_row.update({"debit": balancing_amount, "debit_in_account_currency": balancing_amount})
        je.append("accounts", account_row)

    if not je.accounts:
        frappe.msgprint("No non-zero differences found")
        return

    je.insert()
    frappe.db.commit()
    frappe.msgprint(
        f"Journal Entry draft: {je.name}\n"
        f"Accounts: {len(je.accounts)}\n"
        f"Debit: {flt(max(total_debit, total_credit), 2):.2f}\n"
        f"Credit: {flt(max(total_debit, total_credit), 2):.2f}"
    )


def get_report_rows():
    from erpnext.stock.report.stock_balance.stock_balance import execute

    filters = {
        "company": COMPANY,
        "from_date": FROM_DATE,
        "to_date": TO_DATE,
        "warehouse": "Finished Goods - GPL",
    }
    _, report_rows = execute(filters)
    gl_balances = get_gl_balances()
    rows = []
    for row in report_rows:
        account = get_full_account(row.get("account_number"))
        balance = flt(row.get("bal_val"), 2)
        gl_balance = flt(gl_balances.get(account, 0), 2)
        rows.append({
            "item_code": row.get("item_code"),
            "account": account,
            "difference": flt(balance - gl_balance, 2),
        })
    return rows


def get_full_account(account_number):
    if not account_number:
        return ""
    return frappe.db.get_value(
        "Account",
        {"account_number": account_number, "company": COMPANY, "is_group": 0},
        "name",
    ) or ""


def get_gl_balances():
    rows = frappe.db.sql("""
        SELECT account, SUM(debit - credit) AS balance
        FROM `tabGL Entry`
        WHERE company = %s AND posting_date <= %s AND is_cancelled = 0
        GROUP BY account
    """, (COMPANY, TO_DATE), as_dict=True)
    return {row.account: row.balance for row in rows}
