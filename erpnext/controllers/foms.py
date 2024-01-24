import frappe
from erpnext.accounts.doctype.foms_integration_settings.foms_integration_settings import FomsAPI,is_enable_integration
from frappe.core.doctype.sync_log.sync_log import get_pending_log
from frappe.utils import cint
from erpnext.accounts.party import get_party_details

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
    details = get_party_details(supplier.name, party_type="Supplier")
    farm_id = cint(frappe.db.get_single_value('FOMS Integration Settings', "farm_id"))
    data = {
        "farmId": farm_id,
        "supplierID": supplier.foms_id,
        "supplierRefNo": supplier.name,
        "supplierName": supplier.supplier_name,
        "address": details.address_display or details.company_address_display ,
        "contact": supplier.mobile_no or  details.contact_mobile ,
        "email": supplier.email_id or details.contact_email ,
        "creditLimit": 0,
        "creditTermID": 0,
        "contactPerson": details.contact_person,
        "countryCode": frappe.db.get_single_value('FOMS Integration Settings', "country_id"),
        "rmDeviceIds": "",
        "rmDeviceId":  [],
    }
    res = api.create_or_update_supplier(data)
    if 'supplierID' in res:
        supplier.db_set("foms_id", res['supplierID'])