import frappe

"""
bench --site test3 execute erpnext.patches.v14_0.repair_item.add_material_number_rawmat
"""
# update products material group
def add_material_number_rawmat():
    data = frappe.get_all("Item", {
        "material_group":['is', 'not set', ],
        "item_group": "Raw Material"
    }, ['name', 'item_name'])
    left_items = []
    for d in data:
        if "seed" in d.item_name.lower():
            print("Process seeds", d.name, d.item_name)
            doc = frappe.get_doc("Item", d.name)
            doc.material_group = "Seeds"
            doc.save()
        elif any(n in d.name for n in ['NSB', 'NSA', 'NPB', 'NPA']):
            print("Process nutrient", d.name, d.item_name)
            doc = frappe.get_doc("Item", d.name)
            doc.material_group = "Nutrition"
            doc.save()
        else:
            left_items.append(d)
    for d in left_items:
        print("left for", d.name, ",", d.item_name)

"""
bench --site test3 execute erpnext.patches.v14_0.repair_item.add_material_number_products
"""
# update raw material group
def add_material_number_products():
    data = frappe.get_all("Item", {
        "material_group":['is', 'not set'],
        "item_group": "Products"
    }, ['name', 'item_name'])
    left_items = []
    for d in data:
        if "AV" in d.name:
            print("Process AV", d.name, d.item_name)
            doc = frappe.get_doc("Item", d.name)
            doc.material_group = 'Vegetables (Asian Vegetables)'
            doc.save()
        elif "LV" in d.name:
            print("Process LV", d.name, d.item_name)
            doc = frappe.get_doc("Item", d.name)
            doc.material_group = 'Vegetables (Lettuce)'
            doc.save()
    
    for d in left_items:
        print("left for", d.name, ",", d.item_name)