import frappe, json
from frappe.utils import cint, flt, getdate
from six import string_types

# util: sanitize description by removing editor wrapper tags
def _sanitize_desc(desc):
	if not isinstance(desc, string_types):
		return desc
	return (
		desc.replace('<div class="ql-editor read-mode"><p>', "")
		.replace("</p></div>", "")
	)

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

# change to scheduler 5 minutes each
def read_email_inbox():
	# settings
	enable = cint(frappe.get_value("Buying Settings","Buying Settings", 'enable_supplier_invoice'))
	invoice_email_default = frappe.get_value("Buying Settings","Buying Settings", 'default_email_inbox')
	if not enable or not invoice_email_default:
		return

	# get all communication coming
	email_list = frappe.db.sql("""
	SELECT 
		c.name,
		c.subject,
		c.sender,
		c.creation,
		c.email_account,
		c.reference_name,
		c.reference_doctype
	FROM
		`tabCommunication` c
			LEFT JOIN
		`tabComment` com ON com.reference_doctype = 'Communication'
			AND com.reference_name = c.name
			AND com.comment_type = 'Info'
			AND com.content = 'Checked by AI Agent'
	WHERE
		c.communication_type = 'Communication'
			AND c.sent_or_received = 'Received'
			AND com.name IS NULL
			AND c.email_account = %s
			AND (COALESCE(c.reference_name, '') = ''
			OR COALESCE(c.reference_doctype, '') = '')
	ORDER BY c.creation ASC limit 5
		""", (invoice_email_default), as_dict=1 , debug=0)
	
	# filters
	ignore_list = ["google.com"]
	def check_ignore(sender):
		# because this email has "invoice" in his name (invoices@gmail.com)
		# so we need to ignore the sender if from google itself
		# exp: email security etc
		for d in ignore_list:
			if d in sender:
				return True
		return False


	# process
	for comm in email_list:
		set_checked_ai_status("Communication", comm.name)
		
		if check_ignore(comm.sender):
			continue

		_read_email_inbox(comm.name)

def _read_email_inbox(doc_name):

	doc = frappe.get_doc("Communication", doc_name)
	
	# check more deep
	message = f"{doc.subject}|{doc.content}"
	if not is_invoice(message):
		return
	
	exists = frappe.db.exists("Email Invoice", {"inbox":doc.name})
	if exists:
		return
	else:
		# create email invoice
		em = frappe.new_doc("Email Invoice")
		em.flags.ignore_links = True
		em.flags.ignore_permissions = True
		em.insert()
		em.sync_email(doc = doc)
		em.save()

def get_checked_ai_status(cdt, com_name):
	# get checked status on email receive
	exists = frappe.db.exists("Comment", {
		"reference_name":com_name,
		"reference_doctype": cdt,
		"content":"Checked by AI Agent",
		"comment_type":"Info"
	})
	return exists

def set_checked_ai_status(cdt, com_name):
	# get checked status on email receive
	frappe.get_doc({
		"doctype": "Comment",
		"comment_type": "Info",
		"reference_doctype": cdt,
		"reference_name": com_name,
		"content": "Checked by AI Agent",
		"comment_by": "AI Agent"
	}).insert(ignore_permissions=True)

def is_invoice(text):
	text = text.lower()
	
	invoice_keywords = [
		# English
		"invoice", "tax invoice", "bill to", "invoice number",
		"date of invoice", "tax amount", "invoice total", "amount due",
		
		# Chinese (Simplified)
		"发票", "税务发票", "发票号码", "发票日期", "金额", "总金额",
		
		# Japanese
		"請求書", "税請求書", "請求日", "請求番号", "合計金額", "金額",
		
		# Korean
		"세금계산서", "계산서", "송장", "청구서", "총액", "청구 금액",
		
		# Spanish
		"factura", "factura fiscal", "número de factura", "fecha de factura", "importe", "total a pagar",
		
		# French
		"facture", "numéro de facture", "date de facture", "montant", "total à payer",
		
		# German
		"rechnung", "rechnungsnummer", "rechnungsdatum", "gesamtbetrag", "betrag",
		
		# Portuguese
		"fatura", "número da fatura", "data da fatura", "valor", "total a pagar",
		
		# Italian
		"fattura", "numero fattura", "data fattura", "importo", "totale da pagare",

		# Dutch
		"factuur", "factuurnummer", "factuurdatum", "totaalbedrag", "te betalen bedrag",

		# Russian
		"счет-фактура", "счет", "номер счета", "дата счета", "сумма", "итого к оплате",

		# Arabic (with and without diacritics)
		"فاتورة", "رقم الفاتورة", "تاريخ الفاتورة", "المبلغ", "إجمالي المبلغ", "المبلغ المستحق",

		# Hindi (Devanagari)
		"चालान", "इनवॉइस", "इनवॉइस संख्या", "चालान संख्या", "तिथि", "राशि", "कुल राशि",

		# Indonesia"
		"faktur", "faktur pajak", "tagihan ke", "nomor faktur",
		"tanggal faktur", "jumlah pajak", "total faktur", "jumlah yang harus dibayar",

		"payment", "Purchase", "Billing", "Bill", "Charge"
	]

	return any(keyword in text for keyword in invoice_keywords)



def get_item_context():
	# build item list as base knowledge / context for AI
	context = []
	# we limit to products and enable
	items = frappe.db.sql("""
		SELECT 
			i.name AS item_code, i.item_name, i.marketing_name, i.description
		FROM
			`tabItem` i
		WHERE
			i.disabled = 0
				AND i.item_group = 'Raw Material' and i.item_name not like "(R&D)%" limit 10
	""", as_dict=1)
	for d in items:
		keys = [d.item_name]
		if d.marketing_name:
			keys += [d.marketing_name]
		if d.description:
			keys += [d.description]
		context.append(
			{
				"code": d.item_code,
				"name": d.item_name,
				"desc": _sanitize_desc(d.description),
				"keyword": keys,
			}
		)

	
	return json.dumps(context)

def get_item_context_from_supplier(supplier=""):
	"""
	Ambil konteks item berbasis riwayat pembelian dari supplier tertentu.

	Prioritas sumber: Purchase Invoice (PI) lebih tinggi dari Purchase Order (PO).

	Output akhir berupa list of objects: [{code, name, desc}].
	(Selama proses, deduplikasi tetap memakai dict untuk memilih entri terbaik.)
	"""
	if not supplier:
		return json.dumps({})

	# Gabungkan PI dan PO, beri prioritas (1=PI, 2=PO) lalu urutkan waktu terbaru.
	rows = frappe.db.sql(
		"""
		SELECT item_code, item_name, description, doc_ts, priority FROM (
			SELECT 
				pii.item_code,
				pii.item_name,
				pii.description,
				COALESCE(pi.modified, pi.creation) AS doc_ts,
				1 AS priority
			FROM `tabPurchase Invoice Item` pii
			INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
			WHERE pi.supplier = %s
				AND pi.docstatus IN (1)
				AND COALESCE(pii.item_code, '') <> ''

			UNION ALL

			SELECT 
				poi.item_code,
				poi.item_name,
				poi.description,
				COALESCE(po.modified, po.creation) AS doc_ts,
				2 AS priority
			FROM `tabPurchase Order Item` poi
			INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
			WHERE po.supplier = %s
				AND po.docstatus IN (1)
				AND COALESCE(poi.item_code, '') <> ''
		) t
		ORDER BY priority ASC, doc_ts DESC
		""",
		(supplier, supplier),
		as_dict=1,
	)

	context = {}
	for r in rows:
		code = r.get("item_code")
		if not code or code in context:
			continue

		name = r.get("item_name")
		desc = r.get("description")

		if not name or not desc:
			item_master = frappe.db.get_value(
				"Item", code, ["item_name", "description"], as_dict=True
			)
			if item_master:
				name = name or item_master.get("item_name")
				desc = desc or item_master.get("description")

		context[code]={
			"code": code,
			"name": name or code,
			"desc": _sanitize_desc(desc or ""),
		}

	context_list = [
		{"code": code, "name": v.get("name") or code, "desc": v.get("desc") or ""}
		for code, v in context.items()
	]

	return json.dumps(context_list)

def get_customer_context():
	context = {}
	items = frappe.db.sql("""
		SELECT 
			c.name, c.customer_name
		FROM
			`tabCustomer` c
		WHERE
			c.disabled = 0 AND c.is_frozen = 0
	""", as_dict=1)

	contacts = frappe.db.sql("""
		SELECT 
			dl.link_name as customer_code,
			c.email_id,
			c.first_name,
			c.company_name,
			(SELECT 
					GROUP_CONCAT(DISTINCT ce.email_id
							ORDER BY ce.idx
							SEPARATOR ',')
				FROM
					`tabContact Email` ce
				WHERE
					ce.parent = c.name AND ce.is_primary = 0) AS other_email
		FROM
			`tabDynamic Link` dl
				LEFT JOIN
			`tabContact` c ON c.name = dl.parent
		WHERE
			dl.link_doctype = 'Customer'
	""", as_dict=1)

	# not yet
	# join contacts to customer
	email_map = {}
	for d in contacts:
		other_email = (d.other_email or "").split(",")

		if not other_email and not d.email_id:
			continue
		
		if not d.name in email_map:
			email_map[d.name] = [d.email_id] + other_email
		else:
			em = [d.email_id] + other_email
			email_map[d.name] += em
	

	for d in items:
		if not d.name in context:
			emails = email_map.get(d.name) or []
			context[d.name] = {
				"keyword": d.customer_name,
				"emails":emails
			}
	
	return json.dumps(context)

def get_supplier_context():
	context = []
	
	# Ambil semua supplier aktif
	suppliers = frappe.db.sql("""
		SELECT 
			s.name, s.supplier_name, s.website
		FROM
			`tabSupplier` s
		WHERE
			s.disabled = 0
	""", as_dict=1)

	# Ambil kontak yang terhubung ke supplier
	contacts = frappe.db.sql("""
		SELECT 
			dl.link_name as supplier_code,
			c.email_id,
			c.first_name,
			c.company_name,
			(SELECT 
					GROUP_CONCAT(DISTINCT ce.email_id
							ORDER BY ce.idx
							SEPARATOR ',')
				FROM
					`tabContact Email` ce
				WHERE
					ce.parent = c.name AND ce.is_primary = 0) AS other_email
		FROM
			`tabDynamic Link` dl
				LEFT JOIN
			`tabContact` c ON c.name = dl.parent
		WHERE
			dl.link_doctype = 'Supplier'
	""", as_dict=1)

	# Gabungkan kontak berdasarkan supplier_code
	email_map = {}
	for d in contacts:
		other_email = (d.other_email or "").split(",") if d.other_email else []

		if not other_email and not d.email_id:
			continue
		
		if d.supplier_code not in email_map:
			email_map[d.supplier_code] = [d.email_id] + other_email if d.email_id else other_email
		else:
			em = [d.email_id] + other_email if d.email_id else other_email
			email_map[d.supplier_code] += em

	# Bangun context dictionary
	for s in suppliers:
		emails = email_map.get(s.name) or []
		if s.website:
			emails.append(s.website)
			
		context.append({
			"code":s.name,
			"keyword": s.supplier_name,
			"emails": emails
		})

	return json.dumps(context)

def shipping_context():
	pass

def package_context():
	pass

def make_sales_order(args):
	if not args:
		return
	
	if isinstance(args, string_types):
		args = json.loads(args)

	doc = frappe.new_doc("Sales Order")
	doc.customer = args.get("company_name") #should check exist or not
	for d in args.get("items"):
		item_code = d.get("item_code")
		# temporary use default
		uom = frappe.get_value("Item", item_code, "default_packaging")
		row = doc.append("items")
		row.item_code = item_code
		row.qty = flt(d.get("qty"))
		row.uom = uom
	doc.delivery_date = getdate(args.get("delivery_date"))
	# temporary
	doc.pending_po = 1

	# temporary use default address
	addr = frappe.get_value("Customer", doc.customer, 'customer_primary_address')
	doc.customer_address = addr
	doc.shipping_address_name = addr
	doc.ai_doc = 1
	# add attachment
	doc.save()
	return doc.name

def deep_get(d, path, default=None):
	cur = d
	for p in path:
		try:
			if isinstance(cur, dict):
				cur = cur.get(p, default)
			elif isinstance(cur, list) and isinstance(p, int):
				cur = cur[p]
			else:
				return default
		except (KeyError, IndexError, TypeError):
			return default
	return cur

def get_supplier_payload(suppliers, domains):
	"""
	Build payload containing suppliers, domains, supplier references, and domain map.

	- references: { supplier_code: {keyword: supplier_name, emails: [..]} }
	- domain_map: { domain: [supplier_code, supplier_name] }

	Domains are collected from Supplier.website and email domains of linked Contacts.
	"""

	# Helpers
	def _extract_domain_from_url(url):
		if not url:
			return ""
		url = url.strip().lower()
		# Remove scheme
		if url.startswith("http://"):
			url = url[len("http://"):]
		elif url.startswith("https://"):
			url = url[len("https://"):]
		# Remove credentials if any
		if "@" in url and "/" in url.split("@")[0]:
			url = url.split("@", 1)[1]
		# Strip path and query
		url = url.split("/", 1)[0].split("?", 1)[0]
		# Drop port
		url = url.split(":", 1)[0]
		# Drop common subdomain prefix
		if url.startswith("www."):
			url = url[4:]
		return url

	def _extract_domain_from_email(email):
		if not email or "@" not in email:
			return ""
		return email.split("@", 1)[1].strip().lower()

	def _entity_list(code, name):
		out = []
		for v in (code, name):
			if v and v not in out:
				out.append(v)
		return out

	def _looks_like_domain(s):
		if not isinstance(s, string_types):
			return False
		s = s.strip().lower()
		if not s:
			return False
		if "://" in s or s.startswith("www.") or "/" in s:
			return True
		# bare domains like example.com (avoid names with spaces)
		return "." in s and " " not in s and "@" not in s

	# Normalize inputs: accept JSON or comma-separated strings
	if isinstance(suppliers, string_types):
		try:
			suppliers_in = json.loads(suppliers)
		except Exception:
			suppliers_in = [s.strip() for s in suppliers.split(",") if s and s.strip()]
	else:
		suppliers_in = suppliers or []

	if isinstance(domains, string_types):
		try:
			domains_in = json.loads(domains)
		except Exception:
			domains_in = [d.strip() for d in domains.split(",") if d and d.strip()]
	else:
		domains_in = domains or []

	# Clean suppliers/domains if they look like URLs/domains
	suppliers_display = []
	for s in suppliers_in:
		if _looks_like_domain(s):
			suppliers_display.append(_extract_domain_from_url(s) or s)
		else:
			suppliers_display.append(s)

	# Use only non-domain-like strings for DB query (supplier codes)
	suppliers_for_query = [s for s in suppliers_in if not _looks_like_domain(s)]

	# Clean and de-duplicate domains
	seen_domains = set()
	domains_clean = []
	for d in domains_in:
		dom = _extract_domain_from_url(d) or d
		if dom and dom not in seen_domains:
			seen_domains.add(dom)
			domains_clean.append(dom)

	# Fetch supplier master data
	refs = {}
	domain_map = {}

	# Always fetch all active suppliers (exclude disabled/frozen)
	supplier_rows = frappe.db.sql(
		"""
		SELECT name, supplier_name, website
		FROM `tabSupplier`
		WHERE disabled = 0 AND is_frozen = 0
		""",
		as_dict=1,
	)

	supplier_set = {r.name for r in supplier_rows}

	# Pull linked contacts' emails for these suppliers
	emails_by_supplier = {s: [] for s in supplier_set}
	if supplier_set:
		contact_rows = frappe.db.sql(
			"""
			SELECT 
				dl.link_name AS supplier_code,
				c.email_id AS primary_email,
				(
					SELECT GROUP_CONCAT(DISTINCT ce.email_id ORDER BY ce.idx SEPARATOR ',')
					FROM `tabContact Email` ce
					WHERE ce.parent = c.name AND COALESCE(ce.email_id, '') <> ''
				) AS other_emails
			FROM `tabDynamic Link` dl
			LEFT JOIN `tabContact` c ON c.name = dl.parent
			WHERE dl.link_doctype = 'Supplier' AND dl.link_name IN (%s)
			""" % (", ".join(["%s"] * len(supplier_set))),
			tuple(supplier_set),
			as_dict=1,
		)
		for r in contact_rows:
			emails = []
			if r.primary_email:
				emails.append(r.primary_email)
			if r.other_emails:
				emails.extend([e for e in r.other_emails.split(",") if e])
			if emails:
				cur = emails_by_supplier.get(r.supplier_code) or []
				cur.extend(emails)
				emails_by_supplier[r.supplier_code] = cur

	# Build references and domain map
	for s in supplier_rows:
		code = s.name
		sname = s.supplier_name or code
		# dedupe emails and keep order
		seen = set()
		emails = []
		for e in emails_by_supplier.get(code, []):
			if e and e not in seen:
				seen.add(e)
				emails.append(e)
		refs[code] = {"keyword": sname, "emails": emails}

		# website domain
		wdom = _extract_domain_from_url(s.website)
		if wdom:
			domain_map[wdom] = _entity_list(code, sname)
		# email domains
		for e in emails:
			dom = _extract_domain_from_email(e)
			if dom and dom not in domain_map:
				domain_map[dom] = _entity_list(code, sname)

	payload = {
		"supplier_names": suppliers_display,
		"domains": domains_clean,
		"references": refs,
		"domain_map": domain_map,
	}

	return payload

from erpnext.ai_agent.doctype.ai_agent_settings.ai_invoice_converter import AIAgentClient
def chunks(lst, size):
	for i in range(0, len(lst), size):
		yield lst[i:i + size]

def update_supplier_domain():
	# ambil supplier yang belum ada website
	supplier_data = frappe.db.sql("""
		SELECT name
		FROM `tabSupplier`
		WHERE website IS NULL
		  AND disabled = 0
		  AND supplier_type = 'Company'
	""", as_dict=1)

	payload = [x["name"] for x in supplier_data]
	agent = AIAgentClient()

	for batch in chunks(payload, 20):   # max 50 per panggilan
		res = agent.get_supplier_domain(batch)

		# update tiap hasil
		if 'result' in res:
			res = res.get("result")

		for d in res:
			if d.get("company") and d.get("domain"):
				frappe.db.set_value(
					"Supplier",
					d["company"],
					"website",          # <- tambahkan fieldname yang mau diupdate
					d["domain"]
				)
				print("Set domain", d["company"], d["domain"])

		frappe.db.commit()