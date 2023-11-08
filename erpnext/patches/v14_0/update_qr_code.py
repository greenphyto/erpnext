import frappe


"""
bench --site erp.greenphyto.com execute erpnext.patches.v14_0.update_qr_code.execute
"""
from erpnext.assets.utils import create_asset_qrcode, save_qrcode_image
def execute():
    for d in frappe.get_list("Asset"):
        res = save_qrcode_image("Asset", d.name, 1)
        print("Update QR {} => {}".format(d, frappe.utils.get_url(res)))
