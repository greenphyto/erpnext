import frappe
from frappe.utils import flt
import csv
import os


def get_scrap_rate_comparison():
    entries = frappe.db.sql("""
        SELECT
            se.name AS stock_entry,
            se.posting_date,
            se.posting_time,
            sed.item_code,
            sed.s_warehouse,
            sed.qty,
            sed.basic_rate,
            sed.basic_amount
        FROM `tabStock Entry` se
        JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE se.docstatus = 1
          AND se.stock_entry_type_view = 'Scrap Materials'
          AND se.posting_date >= '2026-02-01'
        ORDER BY se.posting_date DESC, se.name, sed.idx
    """, as_dict=True)

    rate_map = {}

    def get_correct_rate(item_code, warehouse, posting_date, posting_time):
        key = (item_code, warehouse, str(posting_date))
        if key in rate_map:
            return rate_map[key]

        sle = frappe.db.sql("""
            SELECT name, valuation_rate
            FROM `tabStock Ledger Entry`
            WHERE item_code = %s
              AND warehouse = %s
              AND is_cancelled = 0
              AND voucher_type != 'Stock Entry'
              AND (posting_date < %s OR (posting_date = %s AND posting_time <= %s))
            ORDER BY posting_date DESC, posting_time DESC, creation DESC
            LIMIT 1
        """, (item_code, warehouse, posting_date, posting_date, posting_time), as_dict=True)

        rate = flt(sle[0].valuation_rate) if sle else 0
        sle_name = sle[0].name if sle else ""
        rate_map[key] = (rate, sle_name)
        return rate_map[key]

    results = []
    for row in entries:
        correct_rate, sle_name = get_correct_rate(row.item_code, row.s_warehouse, row.posting_date, row.posting_time)
        correct_amount = flt(row.qty * correct_rate, 4)
        results.append({
            "stock_entry": row.stock_entry,
            "posting_date": str(row.posting_date),
            "item_code": row.item_code,
            "s_warehouse": row.s_warehouse,
            "qty": flt(row.qty, 4),
            "current_rate": flt(row.basic_rate, 4),
            "current_amount": flt(row.basic_amount, 4),
            "correct_rate": flt(correct_rate, 4),
            "correct_amount": correct_amount,
            "rate_diff": flt(row.basic_rate - correct_rate, 4),
            "amount_diff": flt(row.basic_amount - correct_amount, 4),
            "sle_ref": sle_name,
        })

    output_path = os.path.expanduser("~/SCRAP_VALUE.csv")
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "stock_entry", "posting_date", "item_code", "s_warehouse",
            "qty", "current_rate", "current_amount", "correct_rate", "correct_amount",
            "rate_diff", "amount_diff", "sle_ref"
        ])
        writer.writeheader()
        writer.writerows(results)

    frappe.msgprint(f"Output written to {output_path} ({len(results)} rows)")
