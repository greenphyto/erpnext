import frappe

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