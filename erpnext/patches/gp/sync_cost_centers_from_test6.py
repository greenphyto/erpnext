import frappe


def execute():
	companies = {
		"Greenphyto Pte Ltd": {
			"abbr": "GPL",
			"root": "Greenphyto Pte Ltd - GPL",
			"group": "GPL 10 - GPL",
		},
		"Greenphyto Tech Sdn Bhd": {
			"abbr": "GTSB",
			"root": "Greenphyto Tech Sdn Bhd - GTSB",
			"group": "GTSB 10 - GTSB",
		},
		"Arber Pte Ltd": {
			"abbr": "APL",
			"root": "Arber Pte Ltd - APL",
			"group": "APL 10 - APL",
		},
	}
	departments = [
		("1010", "Common-Office (Main)", 1),
		("1020", "Finance", 0),
		("1030", "HR", 0),
		("1040", "Sales", 0),
		("1050", "Procurement", 0),
		("1060", "Customer Service", 0),
		("1070", "Digital", 0),
		("1080", "Infrastructure & Maintenance", 0),
		("1090", "CEO Office", 0),
		("2020", "Production-WH", 0),
		("3020", "Production-R&D", 0),
		("4020", "Packing", 0),
		("4030", "Logistics", 0),
		("5010", "System", 0),
	]

	for company, values in companies.items():
		_records = [
			{"name": values["root"], "cost_center_name": company, "company": company, "is_group": 1, "disabled": 0},
			{"name": values["group"], "cost_center_name": values["group"].split(" - ")[0], "company": company, "parent_cost_center": values["root"], "old_parent": values["root"], "is_group": 1, "disabled": 0},
			{"name": f"Main - {values['abbr']}", "cost_center_name": "Main", "company": company, "parent_cost_center": values["root"], "old_parent": values["root"], "is_group": 0, "disabled": 0},
		]
		_records.extend({"name": f"{number} - {name} - {values['abbr']}", "cost_center_name": name, "cost_center_number": number, "company": company, "parent_cost_center": values["group"], "old_parent": values["group"], "is_group": 0, "disabled": disabled} for number, name, disabled in departments)

		for data in _records:
			name = data.pop("name")
			doc = frappe.db.exists("Cost Center", name)
			if doc:
				doc = frappe.get_doc("Cost Center", doc)
				if not data.get("parent_cost_center"):
					continue
				doc.update(data)
				doc.save(ignore_permissions=True)
			else:
				frappe.get_doc({"doctype": "Cost Center", "name": name, **data}).insert(ignore_permissions=True)

	frappe.db.commit()
