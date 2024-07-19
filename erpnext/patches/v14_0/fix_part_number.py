import frappe

def execute():
    fix_raw_material()

def fix_raw_material():
    print(frappe.local.conf)
    data = {
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
    }

    data_reff = list(data.keys())
    print(data_reff)

    num_series = 10
    for d in frappe.db.get_all("Item", {'name':['in', data_reff]}, ['name', 'material_group', 'material_number']):
        new_series = data.get(d.name)
        frappe.db.set_value("Item", d.name, "material_number", new_series)
        print(d, new_series)

    print("Update all")
    for d in frappe.db.get_all("Item", {"material_group":"Seeds", 'name':['not in', data_reff]}, order_by='creation'):
        new_series = 100000 + num_series
        num_series += 1
        frappe.db.set_value("Item", d.name, "material_number", new_series)
        print(d, new_series)

    print("Now", num_series-1)
    frappe.db.sql('update `tabSeries` set current = {} where name = "10" '.format(num_series-1))

