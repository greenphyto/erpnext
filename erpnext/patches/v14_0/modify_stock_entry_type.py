import frappe


# add new Stock Entry Type
# disable old transaction
"""
Seeding Transfer (Series Number should be SE-XXXX/YYYY) 
Transplanting Transfer (Series Number should be TR-XXXXX/YYY
Harvesting Finished Goods (Series Number should be HA-XXXXX/YYYY)
Conversion from Inventory to Fixed Asset (Series Number should ITA-XXXXX/YYYY)
Material Issue (Series Number should be MI-XXXXX/YYYY)
Repack (Series Number should be RE-XXXXX/YYYY)
Move from one warehouse to another (Series Number MW-XXXXX/YYYY
"""

TYPE_MAP = [
    {
        "__newname":"Seeding Transfer",
        "series":"SE-.#####./.YYYY",
        "purpose":"Material Transfer for Manufacture"
    },
    {
        "__newname":"Transplanting Transfer",
        "series":"TR-.#####./.YYYY",
        "purpose":"Material Transfer for Manufacture"
    },
    {
        "__newname":"Harvesting Finished Goods",
        "series":"HA-.#####./.YYYY",
        "purpose":"Manufacture"
    },
    {
        "__newname":"Conversion from Inventory to Fixed Asset",
        "series":"ITA-.#####./.YYYY",
        "purpose":"Material Issue"
    },
    {
        "__newname":"Material Issue",
        "series":"MI-.#####./.YYYY",
        "purpose":"Material Issue"
    },
    {
        "__newname":"Repack",
        "series":"RE-.#####./.YYYY",
        "purpose":"Repack"
    },
    {
        "__newname":"Move from one warehouse to another",
        "series":"MW-.#####./.YYYY",
        "purpose":"Material Transfer"
    },
]

"""
bench --site erp.greenphyto.com execute erpnext.patches.v14_0.modify_stock_entry_type.execute
"""
def execute():
    disable_current_type()
    create_new_type()

"""
bench --site test3 execute erpnext.patches.v14_0.modify_stock_entry_type.create_new_type
"""
def create_new_type():
    for d in TYPE_MAP:
        exists = frappe.db.exists("Stock Entry Type", d['__newname'])
        if exists:
            doc = frappe.get_doc("Stock Entry Type", exists)
            doc.series = d['series']
            doc.purpose = d['purpose']
            doc.save()
            print("Update current type", d['__newname'])
        else:
            doc = frappe.new_doc("Stock Entry Type")
            doc.update(d)
            doc.insert()
            print("Insert new type", doc.name)

"""
bench --site test3 execute erpnext.patches.v14_0.modify_stock_entry_type.disable_current_type
"""
def disable_current_type():
    cur_list = [d.name for d in frappe.db.get_all("Stock Entry Type")]

    cur_sets = [d['__newname'] for d in TYPE_MAP]

    for typ in cur_list:
        if typ not in cur_sets:
            frappe.db.set_value("Stock Entry Type", typ, "disabled", 1)
        else:
            frappe.db.set_value("Stock Entry Type", typ, "disabled", 0)
        

