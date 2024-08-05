import frappe, json


"""
bench --site erp.greenphyto.com execute erpnext.patches.v14_0.update_qr_code.execute
"""
from erpnext.assets.utils import create_asset_qrcode, save_qrcode_image
def execute():
    for d in frappe.get_list("Asset"):
        res = save_qrcode_image("Asset", d.name, 1)
        print("Update QR {} => {}".format(d, frappe.utils.get_url(res)))

"""
bench --site erp.greenphyto.com execute erpnext.patches.v14_0.update_qr_code.update_deleted_date_docuemnt
bench --site test6 execute erpnext.patches.v14_0.update_qr_code.update_deleted_date_docuemnt
"""
def update_deleted_date_docuemnt():
    data = frappe.db.sql("select name, data from `tabDeleted Document` where deleted_doctype in ('Journal Entry', 'Payment Entry')", as_dict=1)
    for d in data:
        dt = frappe._dict(json.loads(d.data))
        print(d.name, dt.name, dt.posting_date)
        frappe.db.set_value("Deleted Document", d.name, "document_date", dt.posting_date)
"""
bench --site test6 execute erpnext.patches.v14_0.update_qr_code.update_weight_item
"""
def update_weight_item():
    frappe.db.sql("""
        UPDATE `tabItem` 
        SET 
            weight_per_unit = 1,
            weight_uom = stock_uom
        WHERE
            weight_per_unit != 1
        AND stock_uom IN ('Kg' , 'Gram', 'Mililitre', 'Litre')
    """)