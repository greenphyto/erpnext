import frappe
from frappe.utils import cstr

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
        "DMC01":"220000"
    },
    "FG - Systems":{
        "ZMSC01":"260000",
        "ZMSC02":"260001",
    }
}

def set_part_number(doc, method=""):
    if doc.material_group in PART_NUMBER_FIX:
        mat_group = PART_NUMBER_FIX[doc.material_group]
        part_number = mat_group.get(doc.item_code)
        doc.material_number = part_number

def execute():
    # Seeds
    # do_sync(PART_NUMBER_FIX['Seeds'], "Seeds", 10, 10)

    # Veg (AV)
    do_sync(PART_NUMBER_FIX['Vegetables (Asian Vegetables)'], 
            "Vegetables (Asian Vegetables)", 15, 6)

    # Veg (LV)
    do_sync(PART_NUMBER_FIX['Vegetables (Lettuce)'], "Vegetables (Lettuce)", 14, 4)

    # # Nutrient
    # do_sync(PART_NUMBER_FIX['Nutrition'], "Nutrition", 11, 2)

    # # Other Packaging
    # do_sync(PART_NUMBER_FIX['Other Packaging'], "Other Packaging", 13, 3)

    # # LED
    # do_sync(PART_NUMBER_FIX['LED'], "LED", 20, 2)

    # # Gateway
    # do_sync(PART_NUMBER_FIX['Gateway'], "Gateway", 21, 1)

    # # Dimmer Controller
    # do_sync(PART_NUMBER_FIX['Dimmer Controller'], "Dimmer Controller", 22, 1)

    # # FG Systems
    # do_sync(PART_NUMBER_FIX['FG - Systems'], "FG - Systems", 22, 2)


def do_sync(data, material_group, series_key, start_from):

    data_reff = list(data.keys())
    print(data_reff)

    idx = start_from
    num_series = series_key * 10000
    for d in frappe.db.get_all("Item", {'name':['in', data_reff]}, ['name', 'material_group', 'material_number']):
        new_series = data.get(d.name)
        frappe.db.set_value("Item", d.name, "material_number", new_series)
        print(d, new_series)

    print("Update all")
    for d in frappe.db.get_all("Item", {"material_group": material_group, 'name':['not in', data_reff]},['name', 'material_group', 'material_number'], order_by='creation'):
        new_series = num_series + idx
        idx += 1
        frappe.db.set_value("Item", d.name, "material_number", new_series)
        print(d, new_series)

    if idx > start_from:
        idx -= 1

    print("Now", idx)
    frappe.db.sql('update `tabSeries` set current = {} where name = %s '.format(idx), cstr(series_key))

