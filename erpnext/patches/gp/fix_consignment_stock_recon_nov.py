import frappe
from collections import defaultdict, deque
from frappe.utils import flt

WAREHOUSE = "Consignment - VILLAGE GROCER - GTSB"
CUTOFF_DATE = "2026-11-01"
CUTOFF_TIME = "00:00:00"
VALUE_GAP_THRESHOLD = 1.0

# bench --site erp-prod execute erpnext.patches.gp.fix_consignment_stock_recon_nov.execute --kwargs "{'dry_run': 1}"
def execute(dry_run=0):
	company = frappe.db.get_value("Warehouse", WAREHOUSE, "company")
	rows = get_expected_rows(company)

	print(f"{'item_code':<12} {'batch_no':<22} {'qty':>10} {'stored_rate':>12} {'new_rate':>12}")
	for row in rows:
		print(
			f"{row.item_code:<12} {row.batch_no or '':<22} {row.qty:>10} "
			f"{row.stored_rate:>12} {row.valuation_rate:>12}"
		)
	print(f"Items: {len({r.item_code for r in rows})}, rows: {len(rows)}")

	if dry_run or not rows:
		return

	existing = frappe.db.get_value(
		"Stock Reconciliation",
		{
			"company": company,
			"purpose": "Stock Reconciliation",
			"set_warehouse": WAREHOUSE,
			"posting_date": CUTOFF_DATE,
			"docstatus": 0,
		},
		"name",
	)
	if existing:
		print(f"Draft already exists: {existing}")
		return

	doc = frappe.new_doc("Stock Reconciliation")
	doc.company = company
	doc.purpose = "Stock Reconciliation"
	doc.set_warehouse = WAREHOUSE
	doc.posting_date = CUTOFF_DATE
	doc.posting_time = CUTOFF_TIME
	doc.set_posting_time = 1
	doc.expense_account = frappe.db.get_value("Company", company, "stock_adjustment_account")
	doc.cost_center = frappe.db.get_value("Company", company, "cost_center")

	for row in rows:
		doc.append(
			"items",
			{
				"item_code": row.item_code,
				"warehouse": WAREHOUSE,
				"batch_no": row.batch_no,
				"qty": row.qty,
				"valuation_rate": row.valuation_rate,
			},
		)

	doc.insert()
	frappe.db.commit()
	print(f"Created draft Stock Reconciliation: {doc.name} ({len(doc.items)} rows)")


def get_expected_rows(company):
	items = {
		d.name: d
		for d in frappe.db.sql(
			"select name, valuation_method from `tabItem`", as_dict=True
		)
	}
	batchwise = {
		d.name: cint_(d.use_batchwise_valuation)
		for d in frappe.db.sql("select name, use_batchwise_valuation from `tabBatch`", as_dict=True)
	}

	source_rate = {}
	for d in frappe.db.sql(
		"""
		select voucher_detail_no, abs(stock_value_difference) / abs(actual_qty) as rate
		from `tabStock Ledger Entry`
		where voucher_type = 'Consignment Order' and actual_qty < 0
			and is_cancelled = 0 and warehouse != %s and actual_qty != 0
		""",
		WAREHOUSE,
		as_dict=True,
	):
		source_rate[d.voucher_detail_no] = d.rate

	sles = frappe.db.sql(
		"""
		select item_code, batch_no, voucher_type, voucher_detail_no, actual_qty,
			incoming_rate, stock_value, stock_value_difference, valuation_rate
		from `tabStock Ledger Entry`
		where warehouse = %s and is_cancelled = 0
			and (posting_date < %s)
		order by item_code, posting_date, posting_time, creation
		""",
		(WAREHOUSE, CUTOFF_DATE),
		as_dict=True,
	)

	buckets = defaultdict(lambda: {"qty": 0.0, "value": 0.0, "queue": deque()})
	batch_qty = defaultdict(float)
	stored_value = {}
	stored_qty = {}
	last_sle = {}

	for s in sles:
		item_code = s.item_code
		method = items[item_code].valuation_method or "FIFO"
		by_batch = bool(s.batch_no and batchwise.get(s.batch_no))
		bucket = buckets[(item_code, s.batch_no if by_batch else "")]
		qty = flt(s.actual_qty)
		last_sle[item_code] = s
		if s.batch_no:
			batch_qty[(item_code, s.batch_no)] += qty

		if qty > 0:
			if s.voucher_type == "Consignment Order" and s.voucher_detail_no in source_rate:
				rate = source_rate[s.voucher_detail_no]
			else:
				rate = flt(s.incoming_rate)
			bucket["qty"] += qty
			bucket["value"] += qty * rate
			bucket["queue"].append([qty, rate])
		elif qty < 0:
			out_qty = -qty
			if bucket["qty"] <= 0:
				rate = flt(s.valuation_rate)
			elif method == "Moving Average" or by_batch:
				rate = bucket["value"] / bucket["qty"]
			else:
				need = out_qty
				total = 0.0
				queue = bucket["queue"]
				while need > 1e-9 and queue:
					take = min(need, queue[0][0])
					total += take * queue[0][1]
					queue[0][0] -= take
					need -= take
					if queue[0][0] <= 1e-9:
						queue.popleft()
				rate = total / out_qty
			bucket["qty"] -= out_qty
			bucket["value"] -= out_qty * rate
			if method == "Moving Average" or by_batch:
				bucket["queue"].clear()
				if bucket["qty"] > 0:
					bucket["queue"].append([bucket["qty"], bucket["value"] / bucket["qty"]])
		else:
			bucket["value"] += flt(s.stock_value_difference)

	item_expected = defaultdict(lambda: [0.0, 0.0])
	for (item_code, _batch), b in buckets.items():
		item_expected[item_code][0] += b["qty"]
		item_expected[item_code][1] += b["value"]

	result = []
	for item_code, (exp_qty, exp_value) in item_expected.items():
		last = last_sle.get(item_code)
		if not last or flt(exp_qty, 4) <= 0:
			continue
		stored = flt(last.stock_value)
		if abs(stored - exp_value) <= VALUE_GAP_THRESHOLD:
			continue

		stored_rate = stored / exp_qty if exp_qty else 0
		item_batches = [
			(batch_no, qty)
			for (code, batch_no), qty in batch_qty.items()
			if code == item_code and flt(qty, 4) > 0
		]

		if item_batches:
			for batch_no, qty in sorted(item_batches):
				if batchwise.get(batch_no):
					b = buckets[(item_code, batch_no)]
					rate = b["value"] / b["qty"] if b["qty"] > 0 else 0
				else:
					rate = exp_value / exp_qty
				result.append(
					frappe._dict(
						item_code=item_code,
						batch_no=batch_no,
						qty=flt(qty, 4),
						valuation_rate=flt(rate, 6),
						stored_rate=flt(stored_rate, 6),
					)
				)
		else:
			result.append(
				frappe._dict(
					item_code=item_code,
					batch_no=None,
					qty=flt(exp_qty, 4),
					valuation_rate=flt(exp_value / exp_qty, 6),
					stored_rate=flt(stored_rate, 6),
				)
			)

	return sorted(result, key=lambda r: (r.item_code, r.batch_no or ""))


def cint_(value):
	return 1 if value else 0
