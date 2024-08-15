import frappe
import csv 
from pathlib import Path

"""
bench --site test2 execute erpnext.patches.v14_0.fix_asset.run_update_asset_name
"""

def execute():
    pass

def run_update_asset_name():
    file = Path(__file__).parent / "asset_name.csv"
    print("Path", file)
    with file.open("r", encoding="utf-8") as data_file:
        csv_data = csv.reader(data_file)
        # print("Get data length:", len(list(csv_data)))
    
        id_col = 0
        item_name_col = 1
        asset_name_col = 2
        csv_data = csv.reader(data_file)
        for d in list(csv_data):
            item = ' '.join(d[id_col].splitlines())
            # print(asset)
            asset_id = frappe.get_value("Asset",{"item_code":item})

            if not asset_id:
                print("Skip for this asset:", item)
                continue
            
            print("Renaming", item)
            if d[item_name_col]:
                new_item_name = d[item_name_col].strip()
                brand = get_brand(new_item_name)
                frappe.db.set_value("Asset", asset_id, "brand", brand)
                frappe.db.set_value("Item", item, "brand", brand)

            if d[asset_name_col]:
                new_asset_name = d[asset_name_col].strip()
                frappe.db.set_value("Asset", asset_id, "asset_name", new_asset_name)

def get_brand(brand):
    exist = frappe.get_value("Brand", brand)
    if not exist:
        doc = frappe.new_doc("Brand")
        doc.brand = brand
        doc.insert()
        return doc.name
    return exist