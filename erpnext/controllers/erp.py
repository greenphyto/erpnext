import frappe, json
from frappe.utils import cint, flt, getdate
from six import string_types

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

def read_email_inbox(doc, method=""):
	if doc.communication_type != "Communication":
		return
	
	enable = cint(frappe.get_value("Buying Settings","Buying Settings", 'enable_supplier_invoice'))
	invoice_email_default = frappe.get_value("Buying Settings","Buying Settings", 'default_email_inbox')
	if not enable or not invoice_email_default:
		return
	
	if doc.email_account != invoice_email_default:
		return
	
	if doc.reference_doctype and doc.reference_name:
		return
	
	message = "Subject: {}\nMessage: {}".format(doc.subject, doc.content)
	if not is_invoice(message):
		return

	# create email invoice
	em = frappe.new_doc("Email Invoice")
	em.sync_email(doc = doc)
	em.flags.ignore_links = True
	em.flags.ignore_permissions = True
	em.save()


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
    ]

    return any(keyword in text for keyword in invoice_keywords)



def get_item_context():
	# build item list as base knowledge / context for AI
	context = {}
	# we limit to products and enable
	items = frappe.db.sql("""
		SELECT 
			i.name AS item_code, i.item_name, i.marketing_name
		FROM
			`tabItem` i
		WHERE
			i.disabled = 0
				AND i.item_group = 'Products' and i.item_name not like "(R&D)%" limit 10
	""", as_dict=1)
	for d in items:
		if not d.item_code in context:
			keys = d.item_name
			if d.marketing_name:
				keys += "/"+d.marketing_name
			context[d.item_code] = {
				"keyword": f'{keys}'
			}
	
	return json.dumps(context)

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
	context = {}
	
	# Ambil semua supplier aktif
	suppliers = frappe.db.sql("""
		SELECT 
			s.name, s.supplier_name
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
		context[s.name] = {
			"keyword": s.supplier_name,
			"emails": emails
		}

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
