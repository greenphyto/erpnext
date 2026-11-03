import frappe, json, csv
from frappe.utils import flt


def run():
    accounts = ("121111 - Stock - Komatsuna Dream - GPL", "121100 - Stock - F1 Hybrid Kailan - GPL")

    # Item FG yang benar-benar milik tiap akun (dari Stock Entry finished item)
    acc_item = {
        "121111 - Stock - Komatsuna Dream - GPL": "PR-AV-DRE",
        "121100 - Stock - F1 Hybrid Kailan - GPL": "PR-AV-KL",
    }

    rows = []

    # DELIVERY NOTE: pasangkan GL akun X hanya ke item FG milik akun X
    for acc, item in acc_item.items():
        dn = frappe.db.sql(
            """
            SELECT 'Delivery Note' AS voucher_type, gl.voucher_no, gl.account,
                   gl.posting_date, %s AS item_code,
                   it.sum_qty AS qty, it.sum_stock_qty AS stock_qty,
                   ABS(gl.debit - gl.credit) AS gl_amount
            FROM `tabGL Entry` gl
            JOIN `tabDelivery Note` dn ON dn.name = gl.voucher_no AND dn.docstatus = 1
            JOIN (
                SELECT parent, SUM(qty) AS sum_qty, SUM(stock_qty) AS sum_stock_qty
                FROM `tabDelivery Note Item`
                WHERE item_code = %s
                GROUP BY parent
            ) it ON it.parent = gl.voucher_no
            WHERE gl.is_cancelled = 0 AND gl.voucher_type = 'Delivery Note'
              AND gl.account = %s AND it.sum_stock_qty > 0
              AND gl.posting_date >= '2026-01-01'
            """, (item, item, acc), as_dict=1)
        rows.extend(dn)

        se = frappe.db.sql(
            """
            SELECT 'Stock Entry' AS voucher_type, gl.voucher_no, gl.account,
                   gl.posting_date, %s AS item_code,
                   it.sum_qty AS qty, it.sum_stock_qty AS stock_qty,
                   ABS(gl.debit - gl.credit) AS gl_amount
            FROM `tabGL Entry` gl
            JOIN `tabStock Entry` se ON se.name = gl.voucher_no AND se.docstatus = 1
            JOIN (
                SELECT parent, SUM(qty) AS sum_qty, SUM(transfer_qty) AS sum_stock_qty
                FROM `tabStock Entry Detail`
                WHERE item_code = %s AND is_finished_item = 1
                GROUP BY parent
            ) it ON it.parent = gl.voucher_no
            WHERE gl.is_cancelled = 0 AND gl.voucher_type = 'Stock Entry'
              AND gl.account = %s AND it.sum_stock_qty > 0
              AND gl.posting_date >= '2026-01-01'
            """, (item, item, acc), as_dict=1)
        rows.extend(se)

    for r in rows:
        r["rate_per_qty"] = round(flt(r["gl_amount"]) / flt(r["stock_qty"]), 4) if flt(r["stock_qty"]) else 0
        r["anomaly_gt_10usd"] = 1 if flt(r["rate_per_qty"]) > 10 else 0

    fields = ["voucher_type", "voucher_no", "posting_date", "account", "item_code", "qty", "stock_qty",
              "gl_amount", "rate_per_qty", "anomaly_gt_10usd"]
    path = "/workspace/development/gp-frappe-bench-v14/apps/erpnext/erpnext/gl_rate_anomaly_121111_121100.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows, key=lambda x: -flt(x["rate_per_qty"])):
            w.writerow(r)

    anomalies = [r for r in rows if r["anomaly_gt_10usd"] == 1]
    print("TOTAL_ROWS::", len(rows))
    print("ANOMALIES::", len(anomalies))
    print("DISTINCT_ANOMALY_VOUCHERS::", len(set(r["voucher_no"] for r in anomalies)))
    print("CSV::", path)
