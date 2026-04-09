import frappe, os
import csv

# bench --site erp-candidate execute erpnext.patches.gp.add_remitance_purpose.execute
def execute():
    init_remitance_purpose()

def init_remitance_purpose():
    files = ['ch_cbpr.csv', 'id_cbpr.csv', 'my_cbpr.csv', 'th_cbpr.csv']
    countries = ['China', 'Indonesia', 'Malaysia', 'Thailand']
    country_id = ['CN', 'ID', 'MY', 'TH']
    for file, country, cid in zip(files, countries, country_id):
        csv_path = os.path.join(
        frappe.get_app_path('erpnext'),
            'patches',
            'files',
            file
        )
        if not os.path.exists(csv_path):
            frappe.throw(f"CSV file not found: {csv_path}")

        with open(csv_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                code = row.get("Code", "").strip()
                purpose = row.get("Purpose", "").strip()

                if not code or not purpose:
                    frappe.log_error(f"Skipping row: {row}", "Remitance Purpose Import")
                    continue

                remitance_purpose = frappe.get_doc({
                    "doctype": "Remitance Purpose",
                    "purpose_code": code,
                    "purpose": purpose,
                    "country": country,
                    "country_id": cid,
                })

                # Cek jika sudah ada, update
                existing = frappe.db.exists("Remitance Purpose", {"purpose_code": code, "country_id": cid})
                if existing:
                    doc = frappe.get_doc("Remitance Purpose", existing)
                    doc.purpose = purpose
                    doc.save(ignore_permissions=True)
                else:
                    remitance_purpose.insert(ignore_permissions=True)
                    print("Add Remitance Purpose", code, purpose )
    frappe.db.commit()