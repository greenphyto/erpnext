import frappe
from frappe.utils import today, get_last_day, getdate

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