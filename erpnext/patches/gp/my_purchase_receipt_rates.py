import os

import frappe
import openpyxl
from openpyxl.styles import Font


COMPANY = "Greenphyto Tech Sdn Bhd"
WAREHOUSES = [
    "Kokubu warehouse - GTSB",
    "Consignment - VILLAGE GROCER - GTSB",
]
FROM_DATE = "2026-01-01"
TO_DATE = "2026-08-31"
OUTPUT_PATH = os.path.expanduser("~/MY_PURCHASE_RECEIPT_RATES.xlsx")
HEADERS = ["Item Code", "Item Name", "Warehouse", "Purchase Receipt Qty", "Purchase Receipt Value", "Average Rate"]

# bench --site erp-prod execute erpnext.patches.gp.my_purchase_receipt_rates.execute
def execute():
    rows = frappe.db.sql(
        """
        SELECT sle.item_code, i.item_name, sle.warehouse,
               SUM(sle.actual_qty) AS qty,
               SUM(sle.stock_value_difference) AS value
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` i ON i.name = sle.item_code
        INNER JOIN `tabPurchase Receipt` pr ON pr.name = sle.voucher_no
        WHERE sle.company = %s
          AND sle.warehouse IN %s
          AND sle.posting_date BETWEEN %s AND %s
          AND sle.voucher_type = 'Purchase Receipt'
          AND sle.actual_qty > 0
          AND sle.is_cancelled = 0
          AND pr.docstatus = 1
        GROUP BY sle.item_code, i.item_name, sle.warehouse
        HAVING SUM(sle.actual_qty) > 0
        ORDER BY sle.warehouse, sle.item_code
        """,
        (COMPANY, tuple(WAREHOUSES), FROM_DATE, TO_DATE),
        as_dict=True,
    )

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "MY Purchase Receipt Rates"
    worksheet.append(HEADERS)
    for row in rows:
        qty = flt(row.qty)
        value = flt(row.value)
        worksheet.append([
            row.item_code,
            row.item_name,
            row.warehouse,
            qty,
            value,
            flt(value / qty) if qty else 0,
        ])

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions
    for cell in worksheet[1]:
        cell.font = Font(bold=True)
    for row in worksheet.iter_rows(min_row=2):
        for cell in row[3:]:
            cell.number_format = "0.00"
    workbook.save(OUTPUT_PATH)
    frappe.msgprint(f"Output written to {OUTPUT_PATH}\nRows: {len(rows)}")


def flt(value):
    return frappe.utils.flt(value, 2)


if __name__ == "__main__":
    execute()
