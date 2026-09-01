import frappe
from frappe.utils import flt
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_stock_balance

COMPANY = "Greenphyto Tech Sdn Bhd"
WAREHOUSE = "Kokubu warehouse - GTSB"
TO_DATE = "2026-08-31"
POSTING_TIME = "23:59:00"


def execute():
	negative_batches = get_negative_batches()
	if not negative_batches:
		frappe.msgprint("No negative batch balances found")
		return

	expense_account = frappe.db.get_value("Company", COMPANY, "stock_adjustment_account")
	cost_center = frappe.db.get_value("Company", COMPANY, "cost_center")
	if not expense_account or not cost_center:
		frappe.throw("Company stock adjustment account and cost center are required")

	reco = frappe.new_doc("Stock Reconciliation")
	reco.purpose = "Stock Reconciliation"
	reco.posting_date = TO_DATE
	reco.posting_time = POSTING_TIME
	reco.set_posting_time = 1
	reco.company = COMPANY
	reco.set_warehouse = WAREHOUSE
	reco.expense_account = expense_account
	reco.cost_center = cost_center

	for batch in negative_batches:
		valuation_rate = get_stock_balance(
			batch.item_code, WAREHOUSE, TO_DATE, POSTING_TIME, with_valuation_rate=True
		)[1]
		reco.append(
			"items",
			{
				"item_code": batch.item_code,
				"warehouse": WAREHOUSE,
				"batch_no": batch.batch_no,
				"qty": 0,
				"valuation_rate": flt(valuation_rate),
			},
		)

	reco.insert()
	frappe.db.commit()
	frappe.msgprint(f"Stock Reconciliation draft: {reco.name}\nItems: {len(reco.items)}")


def get_negative_batches():
	from erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history import execute

	_, rows = execute(
		frappe._dict(
			{
				"company": COMPANY,
				"from_date": TO_DATE,
				"to_date": TO_DATE,
				"warehouse": WAREHOUSE,
			}
		)
	)
	return [
		frappe._dict({"item_code": row[0], "batch_no": row[4], "qty": flt(row[8])})
		for row in rows
		if flt(row[8]) < 0
	]


if __name__ == "__main__":
	execute()
