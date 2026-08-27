import frappe
from frappe.utils import flt


def execute():
    company = "Greenphyto Pte Ltd"
    warehouse = "Finished Goods - GPL"
    item_group = "Products"
    cutoff_date = "2026-01-01"
    end_date = "2026-08-15"
    posting_date = end_date

    stock_reco_name = create_stock_reconciliation(
        company, warehouse, item_group, cutoff_date, end_date, posting_date
    )

    je_name = create_journal_entry(
        company, warehouse, item_group, cutoff_date, end_date, posting_date
    )

    frappe.msgprint(f"Stock Reconciliation: {stock_reco_name}\nJournal Entry: {je_name}")


def get_revaluation_data(warehouse, item_group, cutoff_date, end_date):
    from erpnext.patches.gp.stock_balance_revaluation import (
        get_item_name_map,
        get_account_map,
        get_gl_balance_map,
        get_opening_balance,
        get_manufacturing,
        get_dn_return,
        get_delivery_note,
        get_scrap,
        get_reconciliation,
        get_current_stock,
        group_by_item,
    )

    item_name_map = get_item_name_map(item_group)
    account_map = get_account_map()
    gl_balance_map = get_gl_balance_map(end_date)
    opening_map = get_opening_balance(warehouse, item_group, cutoff_date)

    manufacturing = get_manufacturing(warehouse, item_group, cutoff_date, end_date)
    dn_return = get_dn_return(warehouse, item_group, cutoff_date, end_date)
    delivery_note = get_delivery_note(warehouse, item_group, cutoff_date, end_date)
    scrap = get_scrap(warehouse, item_group, cutoff_date, end_date)
    reconciliation = get_reconciliation(warehouse, item_group, cutoff_date, end_date)

    items = set()
    for rows in (manufacturing, dn_return, delivery_note, scrap, reconciliation):
        for row in rows:
            items.add(row.item_code)
    for item_code in opening_map:
        items.add(item_code)

    mfg_by_item = group_by_item(manufacturing)
    dnr_by_item = group_by_item(dn_return)
    dn_by_item = group_by_item(delivery_note)
    scrap_by_item = group_by_item(scrap)
    recon_by_item = group_by_item(reconciliation)

    result = []
    for item_code in sorted(items):
        mfg_entries = mfg_by_item.get(item_code, [])
        dnr_entries = dnr_by_item.get(item_code, [])
        dn_entries = dn_by_item.get(item_code, [])
        scrap_entries = scrap_by_item.get(item_code, [])
        recon_entries = recon_by_item.get(item_code, [])

        mfg_qty = sum(flt(r.actual_qty) for r in mfg_entries)
        mfg_value = sum(flt(r.stock_value_difference) for r in mfg_entries)
        avg_rate = flt(mfg_value / mfg_qty, 10) if mfg_qty else 0

        dnr_qty = sum(flt(r.actual_qty) for r in dnr_entries if flt(r.actual_qty) > 0)
        dnr_qty += sum(flt(r.actual_qty) for r in dn_entries if flt(r.actual_qty) > 0)
        dn_qty = sum(abs(flt(r.actual_qty)) for r in dn_entries if flt(r.actual_qty) < 0)
        scrap_qty = sum(abs(flt(r.actual_qty)) for r in scrap_entries)
        recon_qty = sum(flt(r.actual_qty) for r in recon_entries)

        opening = opening_map.get(item_code, {})
        opening_qty = flt(opening.get("qty", 0))

        balance_qty = opening_qty + mfg_qty + dnr_qty - dn_qty - scrap_qty + recon_qty
        balance_value = flt(balance_qty * avg_rate, 2)

        current = get_current_stock(item_code, warehouse, end_date)
        current_qty = flt(current.get("actual_qty", 0))

        account = account_map.get(item_code, "")
        current_account_balance = flt(gl_balance_map.get(account, 0))

        diff = flt(balance_value - current_account_balance, 2)

        result.append({
            "item_code": item_code,
            "item_name": item_name_map.get(item_code, item_code),
            "account": account,
            "avg_rate": flt(avg_rate, 2),
            "balance_qty": flt(balance_qty, 2),
            "balance_value": balance_value,
            "current_qty": flt(current_qty, 2),
            "current_account_balance": current_account_balance,
            "diff": diff,
        })

    return result


def get_last_batch(item_code, warehouse, end_date):
    result = frappe.db.sql("""
        SELECT sle.batch_no
        FROM `tabStock Ledger Entry` sle
        WHERE sle.item_code = %s
          AND sle.warehouse = %s
          AND sle.posting_date <= %s
          AND sle.is_cancelled = 0
          AND sle.batch_no IS NOT NULL
          AND sle.qty_after_transaction != 0
        ORDER BY sle.posting_date DESC, sle.posting_time DESC, sle.creation DESC
        LIMIT 1
    """, (item_code, warehouse, end_date), as_dict=True)
    if result:
        return result[0].batch_no
    batch = frappe.db.get_value("Batch", {"item": item_code}, "name")
    return batch


def create_stock_reconciliation(company, warehouse, item_group, cutoff_date, end_date, posting_date):
    data = get_revaluation_data(warehouse, item_group, cutoff_date, end_date)

    expense_account = frappe.db.get_value("Company", company, "stock_adjustment_account")
    cost_center = frappe.db.get_value("Company", company, "cost_center")

    reco = frappe.new_doc("Stock Reconciliation")
    reco.purpose = "Stock Reconciliation"
    reco.posting_date = posting_date
    reco.posting_time = "23:59:00"
    reco.set_posting_time = 1
    reco.company = company
    reco.set_warehouse = warehouse
    reco.expense_account = expense_account
    reco.cost_center = cost_center

    for d in data:
        if not d["balance_qty"] and not d["avg_rate"]:
            continue
        batch_no = get_last_batch(d["item_code"], warehouse, end_date)
        reco.append("items", {
            "item_code": d["item_code"],
            "warehouse": warehouse,
            "qty": d["balance_qty"],
            "valuation_rate": d["avg_rate"],
            "batch_no": batch_no,
        })

    reco.insert()
    frappe.db.commit()
    return reco.name


def create_journal_entry(company, warehouse, item_group, cutoff_date, end_date, posting_date):
    data = get_revaluation_data(warehouse, item_group, cutoff_date, end_date)

    cost_center = frappe.db.get_value("Company", company, "cost_center")
    expense_account = frappe.db.get_value("Company", company, "stock_adjustment_account")

    account_diffs = {}
    account_remarks = {}
    for d in data:
        if not d["account"] or not d["diff"]:
            continue
        account_diffs[d["account"]] = account_diffs.get(d["account"], 0) + d["diff"]
        if d["account"] not in account_remarks:
            account_remarks[d["account"]] = []
        account_remarks[d["account"]].append(f"{d['item_code']} ({d['diff']:+.2f})")

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = posting_date
    je.company = company
    je.user_remark = f"Stock balance revaluation as at {posting_date}"

    total_debit = 0
    total_credit = 0

    for account, net_diff in sorted(account_diffs.items()):
        if not net_diff:
            continue
        remark = ", ".join(account_remarks[account])
        if net_diff > 0:
            je.append("accounts", {
                "account": account,
                "debit_in_account_currency": flt(net_diff, 2),
                "debit": flt(net_diff, 2),
                "cost_center": cost_center,
                "user_remark": remark,
            })
            total_debit += flt(net_diff, 2)
        else:
            je.append("accounts", {
                "account": account,
                "credit_in_account_currency": flt(abs(net_diff), 2),
                "credit": flt(abs(net_diff), 2),
                "cost_center": cost_center,
                "user_remark": remark,
            })
            total_credit += flt(abs(net_diff), 2)

    if total_debit > total_credit:
        je.append("accounts", {
            "account": expense_account,
            "credit_in_account_currency": flt(total_debit - total_credit, 2),
            "credit": flt(total_debit - total_credit, 2),
            "cost_center": cost_center,
            "user_remark": "Rounding / balancing",
        })
    elif total_credit > total_debit:
        je.append("accounts", {
            "account": expense_account,
            "debit_in_account_currency": flt(total_credit - total_debit, 2),
            "debit": flt(total_credit - total_debit, 2),
            "cost_center": cost_center,
            "user_remark": "Rounding / balancing",
        })

    je.insert()
    frappe.db.commit()
    return je.name
