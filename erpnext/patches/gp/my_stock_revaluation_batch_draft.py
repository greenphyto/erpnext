import frappe
from frappe.utils import flt


COMPANY = "Greenphyto Tech Sdn Bhd"
KOKUBU = "Kokubu warehouse - GTSB"
CONSIGNMENT = "Consignment - VILLAGE GROCER - GTSB"
WAREHOUSES = [KOKUBU, CONSIGNMENT]
FROM_DATE = "2026-01-01"
TO_DATE = "2026-08-31"

# bench --site erp-prod execute erpnext.patches.gp.my_stock_revaluation_batch_draft.execute
def execute():
    created = []
    rates = get_purchase_receipt_rates()
    expense_account = frappe.db.get_value("Company", COMPANY, "stock_adjustment_account")
    cost_center = frappe.db.get_value("Company", COMPANY, "cost_center")

    for warehouse in WAREHOUSES:
        name = frappe.db.get_value(
            "Stock Reconciliation",
            {
                "company": COMPANY,
                "purpose": "Stock Reconciliation",
                "set_warehouse": warehouse,
                "posting_date": TO_DATE,
                "docstatus": 0,
            },
            "name",
        )
        if not name:
            frappe.msgprint(f"No existing draft found: {warehouse}")
            continue
        reco = frappe.get_doc("Stock Reconciliation", name)
        reco.set("items", [])

        stock_items = get_stock_balance_items(warehouse)
        batches = get_batch_balance(warehouse)
        for item_code, target_qty in stock_items.items():
            batch_rows = batches.get(item_code, [])
            new_rate = rates.get(KOKUBU, {}).get(item_code)
            if new_rate is None:
                continue
            if batch_rows:
                difference = flt(target_qty - sum(row.qty for row in batch_rows), 2)
                batch_rows[-1].qty = flt(batch_rows[-1].qty + difference, 2)
            for batch in batch_rows:
                if flt(batch.qty, 2) <= 0 or flt(new_rate, 2) <= 0:
                    continue
                reco.append("items", {
                    "item_code": item_code,
                    "warehouse": warehouse,
                    "batch_no": batch.batch_no,
                    "qty": flt(batch.qty, 2),
                    "valuation_rate": flt(new_rate, 2),
                })

        reco.save()
        created.append(f"{warehouse}: {reco.name} ({len(reco.items)} items)")

    frappe.db.commit()
    frappe.msgprint("MY Stock Reconciliation drafts:\n" + "\n".join(created) if created else "No MY stock rate changes found")


def get_stock_balance_items(warehouse):
    from erpnext.stock.report.stock_balance.stock_balance import execute

    _, rows = execute({
        "company": COMPANY,
        "from_date": TO_DATE,
        "to_date": TO_DATE,
        "warehouse": warehouse,
    })
    return {row.get("item_code"): flt(row.get("bal_qty"), 2) for row in rows if flt(row.get("bal_qty"), 2) > 0}


def get_batch_balance(warehouse):
    from erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history import execute

    _, rows = execute(frappe._dict({
        "company": COMPANY,
        "from_date": TO_DATE,
        "to_date": TO_DATE,
        "warehouse": warehouse,
    }))
    result = {}
    for row in rows:
        qty = flt(row[8], 2)
        if qty > 0:
            result.setdefault(row[0], []).append(frappe._dict({"batch_no": row[4], "qty": qty}))
    return result



def get_purchase_receipt_rates():
    rows = frappe.db.sql(
        """
        SELECT sle.warehouse, sle.item_code,
               SUM(sle.actual_qty) AS qty,
               SUM(sle.stock_value_difference) AS value
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabPurchase Receipt` pr ON pr.name = sle.voucher_no
        WHERE sle.company = %s
          AND sle.warehouse IN %s
          AND sle.posting_date BETWEEN %s AND %s
          AND sle.voucher_type = 'Purchase Receipt'
          AND sle.actual_qty > 0
          AND sle.is_cancelled = 0
          AND pr.docstatus = 1
        GROUP BY sle.warehouse, sle.item_code
        HAVING SUM(sle.actual_qty) > 0
        """,
        (COMPANY, tuple(WAREHOUSES), FROM_DATE, TO_DATE),
        as_dict=True,
    )
    rates = {warehouse: {} for warehouse in WAREHOUSES}
    for row in rows:
        if flt(row.qty):
            rates[row.warehouse][row.item_code] = flt(row.value / row.qty, 2)
    rates[CONSIGNMENT] = rates[KOKUBU].copy()
    return rates


if __name__ == "__main__":
    execute()
