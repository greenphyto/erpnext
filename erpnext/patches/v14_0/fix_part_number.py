import frappe
from frappe.utils import cstr, cint

PART_NUMBER_FIX = {
    "Seeds":{
        "RM-SD-CR": "100000",
        "RM-SD-CS": "100001",
        "RM-SD-WC": "100002",
        "RM-SD-GN": "100003",
        "RM-SD-CC": "100004",
        "RM-SD-GM": "100005",
        "RM-SD-RB": "100006",
        "RM-SD-NB": "100007",
        "RM-SD-PC": "100008",
        "RM-SD-KL": "100009"
    },
    "Nutrition":{
        "RM-NS-NSA":"110000",
        "RM-NS-NSB":"110001",
        "RM-NS-WW":"110002",
        "RM-NS-OA":"110003"
    },
    "Other Packaging":{
        "ZOT01":"130000",
        "ZOT02":"130001",
        "ZOT03":"130002",
    },
    "Vegetables (Lettuce)":{
        "PR-LV-CR":"140000",
        "PR-LV-CC":"140001",
        "PR-LV-GM":"140002",
        "PR-LV-RB":"140003",
    },
    "Vegetables (Asian Vegetables)":{
        "PR-AV-CS":"150000",
        "PR-AV-WC":"150001",
        "PR-AV-GN":"150002",
        "PR-AV-NB":"150003",
        "PR-AV-PC":"150004",
        "PR-AV-KL":"150005",
    },
    "LED":{
        "PDLED01":"200000",
        "PDLED02":"200001",
    },
    "Gateway":{
        "ZGW01":"210000"
    },
    "Dimmer Controller":{
        "DMC01":"220000",
        "DMC02":"220001"
    },
    "Power Connector":{
        "POC01":"230000",
        "POC02":"230001"
    },
    "FG - Systems":{
        "ZMSC01":"260000",
        "ZMSC02":"260001",
    },
    "Trays & Boards":{
        "PD-TR":"270000",
        "PD-A":"270001",
        "PD-B":"270002",
        "PD-C":"270003",
    },
    "Tooling & Moulding":{
        "TOM01":"280000",
        "TOM02":"280001",
        "TOM03":"280002",
        "TOM04":"280003",
        "TOM05":"280004",
        "TOM06":"280005",
    },
    "Accessories":{
        "ACC01": "290000",
        "ACC02": "290001",
        "ACC03": "290002"
    } 
}

def set_part_number(doc, method=""):
    if doc.material_group in PART_NUMBER_FIX:
        mat_group = PART_NUMBER_FIX[doc.material_group]
        part_number = mat_group.get(doc.item_code)
        doc.material_number = part_number

"""
bench --site test3 execute erpnext.patches.v14_0.fix_part_number.execute
"""
def execute():
    # Seeds
    do_sync(PART_NUMBER_FIX['Seeds'], "Seeds", 10, 10)

    # Nutrient
    do_sync(PART_NUMBER_FIX['Nutrition'], "Nutrition", 11, 4)

    # Other Packaging
    do_sync(PART_NUMBER_FIX['Other Packaging'], "Other Packaging", 13, 3)

    # Veg (LV)
    do_sync(PART_NUMBER_FIX['Vegetables (Lettuce)'], "Vegetables (Lettuce)", 14, 4)
    
    # Veg (AV)
    do_sync(PART_NUMBER_FIX['Vegetables (Asian Vegetables)'], 
            "Vegetables (Asian Vegetables)", 15, 6)

    # LED
    do_sync(PART_NUMBER_FIX['LED'], "LED", 20, 2)

    # Gateway
    do_sync(PART_NUMBER_FIX['Gateway'], "Gateway", 21, 1)

    # Dimmer Controller
    do_sync(PART_NUMBER_FIX['Dimmer Controller'], "Dimmer Controller", 22, 2)

    # Power Connector
    do_sync(PART_NUMBER_FIX['Power Connector'], "Power Connector", 23, 2)

    # FG Systems
    do_sync(PART_NUMBER_FIX['FG - Systems'], "FG - Systems", 26, 2)

    # Trays & Boards
    do_sync(PART_NUMBER_FIX['Trays & Boards'], "Trays & Boards", 27, 4)

    # Tooling & Moulding
    do_sync(PART_NUMBER_FIX['Tooling & Moulding'], "Tooling & Moulding", 28, 6)


def do_sync(data, material_group, series_key, start_from):
    print("update group type:", material_group)
    data_reff = list(data.keys())

    idx = start_from
    num_series = series_key * 10000
    for d in frappe.db.get_all("Item", {'name':['in', data_reff]}, ['name', 'material_group', 'material_number']):
        new_series = data.get(d.name)
        if cint(d.material_number) != cint(new_series):
            frappe.db.set_value("Item", d.name,"material_number", new_series)
            print("update NUMBER'", d.name, d.material_number, new_series)
        elif d.material_group != material_group:
            frappe.db.set_value("Item", d.name,"material_group", material_group)
            print("update GROUP'",  d.name, d.material_group, material_group)
        else:
            print("not updated on'", d.name, d.material_number, new_series)

    for d in frappe.db.get_all("Item", {"material_group": material_group, 'name':['not in', data_reff]},['name', 'material_group', 'material_number'], order_by='creation'):
        new_series = num_series + idx
        idx += 1
        if cint(d.material_number) != cint(new_series):
            frappe.db.set_value("Item", d.name, "material_number", new_series)
            print("update NUMBER", d.name, d.material_number, new_series)
        else:
            print("not updated on", d.name, d.material_number, new_series)

    if idx > start_from:
        idx -= 1

    print("Update current series to", idx)
    frappe.db.sql('update `tabSeries` set current = {} where name = %s '.format(idx), cstr(series_key))
    print("\n")
