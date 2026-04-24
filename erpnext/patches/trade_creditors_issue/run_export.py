"""
Run this script via bench execute:
bench --site test5 execute erpnext.patches.trade_creditors_issue.run_export.run_export
"""
import frappe
from erpnext.patches.trade_creditors_issue.app import export_invoice_noumber

def run_export():
    """Wrapper function to run the export with frappe initialized"""
    return export_invoice_noumber()

if __name__ == "__main__":
    run_export()
