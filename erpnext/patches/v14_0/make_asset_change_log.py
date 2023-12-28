import frappe
from frappe.core.doctype.sync_log.sync_log import create_log

def execute():
    assets = frappe.db.get_all("Asset", {"docstatus":1})
    for asset in assets:
        create_log("Asset", asset.name)