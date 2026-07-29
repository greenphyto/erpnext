from frappe import _


def get_data(data=None):
    if not data:
        data = {}

    data["fieldname"] = "work_order"
    data["non_standard_fieldnames"] = {
        "Batch": "reference_name",
    }
    data["internal_links"] = {
        "Production Plan": ["production_plan", "name"],
        "Stock Entry": ["work_order", "name"],
    }

    existing_labels = [t["label"] for t in data.get("transactions", [])]
    new_groups = [
        {"label": _("Manufacture"), "items": [
            "Request", "Production Plan", "Stock Entry", "Job Card",
            "Workstation", "Workstation Type", "Workstation Property",
            "Operation"
        ]},
        {"label": _("Material"), "items": [
            "Material Request", "Stock Ledger Entry", "Stock Reconciliation"
        ]},
    ]

    for group in new_groups:
        if group["label"] not in existing_labels:
            data["transactions"] = data.get("transactions", []) + [group]

    return data
