import frappe
from frappe.utils import today, get_last_day, getdate, today, get_last_day

def check_email_status(log, method=""):
	if log.status != "Sent":
		return
	
	comm_name = frappe.get_value("Communication", {"message_id":log.message_id})
	if not comm_name:
		return
	
	doc = frappe.get_doc("Communication", comm_name)
	if not doc.reference_doctype and doc.reference_name:
		return
	
	if doc.reference_doctype in ["Purchase Order"]:
		frappe.db.set_value(doc.reference_doctype, doc.reference_name, "email_status", "Y")

	notif = frappe.get_doc("Notification", "Email Sent Status")
	notif.send(doc)

def reminder_submit_invoice():
	if getdate(today()) != get_last_day(today()):
		return
	
	doc_notif = frappe.get_doc("Notification", "Submit Invoice Draft")
	
	# get list invoice
	doc_list = frappe.db.sql("""
		SELECT
			name,
			customer,
			posting_date,
			grand_total,
			currency
		FROM
			`tabSales Invoice`
		WHERE
			docstatus = 0
			AND posting_date <= LAST_DAY(CURDATE())
		ORDER BY
			posting_date ASC
	""", as_dict=1)

	if not doc_list:
		return

	doc = frappe._dict({
		"doc_list":doc_list
	})
	doc_notif.send(doc)

# fixing
from erpnext.stock.get_item_details import get_item_price
def fix_si_discount_ledger(si_name=""):
	# get all 
	if not si_name:
		si_list = frappe.db.sql("""
				SELECT 
					si.name AS sales_invoice,
					si.customer,
					sii.item_code,
					sii.qty,
					sii.uom,
					sii.rate,
					sii.price_list_rate,
					sii.discount_amount,
					sii.discount_account,
					si.posting_date
				FROM
					`tabSales Invoice` si
						JOIN
					`tabSales Invoice Item` sii ON si.name = sii.parent
				WHERE
					sii.discount_amount > 0
						AND si.posting_date > '2025-08-01'
						AND si.docstatus = 1
				GROUP BY si.name
				ORDER BY si.posting_date DESC		  
		""", as_dict=1)
	else:
		si_list = [si_name]

	for dt in si_list:
		si_name = dt.sales_invoice
		doc = frappe.get_doc("Sales Invoice", si_name)
		account = frappe.get_cached_value("Company", doc.company, "default_discount_account")
		if doc.docstatus == 1:
			doc.cancel()

		doc.db_set("docstatus", 0)
		doc.docstatus = 0
		doc.save()

		for d in doc.get("items"):
			item_price_args = {
				"item_code": d.item_code,
				"price_list": "Standard Selling",
				"customer": doc.get("customer"),
				"uom": d.get("uom"),
				"transaction_date": doc.get("posting_date"),
				"batch_no": d.get("batch_no"),
			}
			d.discount_account = account
			temp = get_item_price(item_price_args, d.item_code)
			if temp:
				temp = temp[0]

			d.price_list_rate = temp[1]
		
		doc.save()
		print('\n', doc.name)
		for d in doc.get("items"):
			print(d.item_code, d.price_list_rate, d.discount_account, d.discount_amount, d.total_discount_amount)

		doc.submit()
		# cancel 
		# change draft
		# submit again
		# add discount account

def reminder_submit_purchase_invoice(force=False):
	if getdate(today()).day != 5 and not frappe.flags.in_test and not force:
		return
	
	if not frappe.db.exists("Notification", "Submit Purchase Invoice Draft"):
		return
	
	doc_notif = frappe.get_doc("Notification", "Submit Purchase Invoice Draft")
	
	# get list invoice
	doc_list = frappe.db.sql("""
		SELECT
			name,
			supplier,
			posting_date,
			grand_total,
			currency,
			owner
		FROM
			`tabPurchase Invoice`
		WHERE
			docstatus = 0
			AND posting_date <= LAST_DAY(CURDATE())
		ORDER BY
			posting_date ASC
	""", as_dict=1)

	if not doc_list:
		return

	doc = frappe._dict({
		"doc_list":doc_list
	})
	doc_notif.send(doc)

# send notif if any different found
def detect_work_order_different(doc, method=""):
    if doc.status != "Completed":
        return

    data = frappe.db.sql("""
        SELECT 
            *
        FROM
            (SELECT 
                se.work_order AS work_order,
                wo.creation,
                gl.account,
                se.name AS SE,
                se.posting_date AS se_date,
                SUM(gl.debit) AS total_debit,
                SUM(gl.credit) AS total_credit,
                SUM(gl.debit) - SUM(gl.credit) AS diff
            FROM
                `tabGL Entry` gl
            JOIN `tabStock Entry` se 
                ON gl.voucher_type = 'Stock Entry'
                AND gl.voucher_no = se.name
            LEFT JOIN `tabWork Order` wo 
                ON wo.name = se.work_order
            WHERE
                se.work_order IS NOT NULL
                AND gl.is_cancelled = 0
                AND wo.status = 'Completed'
                AND wo.name = %s
                AND gl.account IN (
                    '121303 - Stock - Harvesting WIP - GPL',
                    '121301 - Stock - Seeding WIP - GPL',
                    '121302 - Stock - Transplanting WIP - GPL',
                    '501060 - Stock Adjustment - GPL'
                )
            GROUP BY se.work_order, gl.account
            ORDER BY wo.creation, se.work_order
            ) t
        WHERE ABS(t.diff) > 0.1
    """, (doc.name,), as_dict=1)

    if not data:
        return  # no issue, do nothing

    # Build HTML table
    rows = ""
    for d in data:
        rows += f"""
            <tr>
                <td>{d.work_order}</td>
                <td>{d.creation}</td>
                <td>{d.SE}</td>
                <td>{d.se_date}</td>
                <td>{d.account}</td>
                <td style="text-align:right;">{d.total_debit:.2f}</td>
                <td style="text-align:right;">{d.total_credit:.2f}</td>
                <td style="text-align:right; color:red;">{d.diff:.2f}</td>
            </tr>
        """

    message = f"""
        <p>Hello Team,</p>
        <p>We detected a difference in GL values for Work Order 
        <a href="{frappe.utils.get_url()}/app/work-order/{doc.name}">{doc.name}</a>. 
        Please review the details below:</p>

        <table border="1" cellspacing="0" cellpadding="4" style="border-collapse: collapse;">
            <tr>
                <th>Work Order</th>
                <th>Creation</th>
                <th>Stock Entry</th>
                <th>Date</th>
                <th>Account</th>
                <th>Total Debit</th>
                <th>Total Credit</th>
                <th>Diff</th>
            </tr>
            {rows}
        </table>

        <p>Regards,<br>ERP Notification</p>
    """

    frappe.sendmail(
        recipients=["rizky@greenphyto.com", "weiquan@greenphyto.com"],   # bisa list lebih dari satu
        subject="🚨 Different Value on Work Order",
        message=message
    )
