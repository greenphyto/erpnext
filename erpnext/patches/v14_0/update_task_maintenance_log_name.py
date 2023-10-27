import frappe
from frappe.model.naming import parse_naming_series


def execute():
    data = frappe.db.get_all("Asset Maintenance Task", {"name":['not like', "TASK%"]})
    for d in data:
        series = "TASK.#####"
        new_name = parse_naming_series(series)
        print(d.name, new_name)
        frappe.rename_doc("Asset Maintenance Task", d.name, new_name, force=1)