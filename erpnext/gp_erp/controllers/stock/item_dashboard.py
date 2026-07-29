from frappe import _


def get_data(data=None):
    if not data:
        data = {}

    data["internal_links"] = {
        "Sales Order": ["items", "sales_order"],
    }

    existing_labels = [t["label"] for t in data.get("transactions", [])]
    new_groups = [
        {"label": _("Manufacture"), "items": [
            "Request", "Production Plan", "Work Order", "Item Manufacturer"
        ]},
        {"label": _("Order"), "items": [
            "Quotation", "Sales Order", "Purchase Order"
        ]},
        {"label": _("Stock"), "items": [
            "Stock Entry", "Stock Ledger Entry", "Bin",
            "Material Request", "Pick List", "Stock Reconciliation"
        ]},
        {"label": _("Accounting"), "items": [
            "Journal Entry", "Payment Entry", "Payment Reconciliation"
        ]},
        {"label": _("Pricing"), "items": [
            "Pricing Rule", "Item Price"
        ]},
    ]

    for group in new_groups:
        if group["label"] not in existing_labels:
            data["transactions"] = data.get("transactions", []) + [group]

    return data
