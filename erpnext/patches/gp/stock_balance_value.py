import os

import frappe
import openpyxl
from openpyxl.styles import Font


COMPANY = "Greenphyto Pte Ltd"
WAREHOUSE = "Finished Goods - GPL"
FROM_DATE = "2026-06-01"
TO_DATE = "2026-08-15"
HEADERS = [
    "Item Code",
    "Item Name",
    "BS Account",
    "Stock Balance Qty",
    "Stock Balance Value",
    "BS Account Balance",
    "Difference",
]


def execute():
    report_rows = get_stock_balance_report()
    accounts = get_accounts()
    gl_balances = get_gl_balances()
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Stock Balance Value"
    worksheet.append(HEADERS)

    for report_row in report_rows:
        account_code = report_row.get("account_number") or ""
        account = get_full_account(account_code) or accounts.get(report_row.get("item_code"), "")
        stock_value = flt(report_row.get("bal_val"))
        account_balance = flt(gl_balances.get(account))
        worksheet.append([
            report_row.get("item_code"),
            report_row.get("item_name"),
            account,
            flt(report_row.get("bal_qty")),
            stock_value,
            account_balance,
            flt(stock_value - account_balance),
        ])

    format_worksheet(worksheet)
    output_path = os.path.expanduser("~/STOCK_BALANCE_VALUE.xlsx")
    workbook.save(output_path)
    frappe.msgprint(f"Output written to {output_path}\nItems: {len(report_rows)}")


def get_stock_balance_report():
    from erpnext.stock.report.stock_balance.stock_balance import execute

    _, rows = execute({
        "company": COMPANY,
        "from_date": FROM_DATE,
        "to_date": TO_DATE,
        "warehouse": WAREHOUSE,
    })
    return rows


def get_accounts():
    rows = frappe.db.sql("""
        SELECT code, account_code
        FROM `tabPart Number Details`
        WHERE parent = %s
          AND account_code IS NOT NULL
          AND account_code != ''
    """, (COMPANY,), as_dict=True)
    return {row.code: row.account_code for row in rows}


def get_full_account(account_code):
    if not account_code:
        return ""
    return frappe.db.get_value(
        "Account",
        {"account_number": account_code, "company": COMPANY, "is_group": 0},
        "name",
    ) or ""


def get_gl_balances():
    rows = frappe.db.sql("""
        SELECT account, SUM(debit - credit) AS balance
        FROM `tabGL Entry`
        WHERE company = %s
          AND posting_date <= %s
          AND is_cancelled = 0
        GROUP BY account
    """, (COMPANY, TO_DATE), as_dict=True)
    return {row.account: row.balance for row in rows}


def flt(value, precision=2):
    return frappe.utils.flt(value, precision)


def format_worksheet(worksheet):
    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions
    for cell in worksheet[1]:
        cell.font = Font(bold=True)
    for row in worksheet.iter_rows(min_row=2):
        for cell in row[3:]:
            cell.number_format = "0.00"


if __name__ == "__main__":
    execute()
