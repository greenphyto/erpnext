import frappe
from erpnext.accounts.doctype.foms_integration_settings.foms_integration_settings import FomsAPI,is_enable_integration
from frappe.core.doctype.sync_log.sync_log import get_pending_log
from frappe.utils import cint

"""
Make Supplier from ERP to FOMS
can update or delete
supplierID = foms_id
"""
def update_foms_supplier():
    if not is_enable_integration():
        return 
    
    logs = get_pending_log({"doctype":"Supplier"})
    api = FomsAPI()
    for log in logs:
        # create new supplier if not have
        if log.update_type == "Update":
            _update_foms_supplier(api, log) 

def _update_foms_supplier(api, log):
    supplier = frappe.get_doc("Supplier", log.name)
    farm_id = cint(frappe.db.get_single_value('FOMS Integration Settings', "farm_id"))
    data = {
        "farmId": farm_id,
        "supplierID": supplier.foms_id,
        "supplierRefNo": supplier.name,
        "supplierName": supplier.supplier_name,
        "address": "Street 512",
        "contact": supplier.mobile_no or '123',
        "email": supplier.email_id or 'test@example.com',
        "creditLimit": 0,
        "creditTermID": 0,
        "contactPerson": "Johandy",
        "countryCode": frappe.db.get_single_value('FOMS Integration Settings', "country_id"),
        "rmDeviceIds": "",
        "rmDeviceId":  [],
    }
    res = api.create_or_update_supplier(data)
    if 'supplierID' in res:
        supplier.db_set("farm_id", res['supplierID'])