import frappe

def execute():
    """Patch: 
    1. Update missing global_description in UOM to match UOM name.
    2. Sync all Item UOMs (global_description, origin_description).
    """

    # Step 1: Update UOM master
    print("Step 1: Updating UOM global_description...")
    uoms = frappe.get_all("UOM", fields=["name", "global_description"])
    for u in uoms:
        if not u.global_description:
            frappe.db.set_value("UOM", u.name, "global_description", u.name)

    # Step 2 & 3: Update Item.uoms child table
    print("Step 2 & 3: Updating Item UOMs...")
    items = frappe.get_all("Item", fields=["name", "stock_uom"])
    for item in items:
        # get child table rows
        rows = frappe.get_all(
            "UOM Conversion Detail",
            filters={"parent": item.name, "parenttype": "Item"},
            fields=["name", "uom", "global_description", "origin_description"]
        )

        for row in rows:
            master_desc = frappe.db.get_value("UOM", row.uom, "global_description")

            # update child row values
            frappe.db.set_value("UOM Conversion Detail", row.name, {
                "global_description": master_desc,
                "origin_description": master_desc
            })

    print("Patch completed successfully ✅")
