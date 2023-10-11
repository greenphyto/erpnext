import frappe

def execute():
    create_non_stock_item()

def create_non_stock_item():
    if frappe.db.get_single_value("Buying Settings", "non_stock_item"):
        return

    item_group = frappe.get_value("Item Group", {"lft":1})

    item = frappe.new_doc("Item")
    item.item_code = "Non-stock"
    item.item_name = "Non-stock"
    item.is_stock_item = 0
    item.is_fixed_asset = 0
    item.stock_uom = "Nos"
    item.item_group = item_group
    item.description = "Non stock / Non fixed asset"
    item.insert()

    
    frappe.db.set_value("Buying Settings", "Buying Settings", "non_stock_item", item.name)

    print("Done create non-stock item {}".format(item.name))