import csv
import os
import frappe

def execute():
    csv_path = os.path.join(
        frappe.get_app_path('erpnext'),
        'patches',
        'files',
        'bank_swift.csv'
    )

    if not os.path.exists(csv_path):
        frappe.throw(f"CSV file not found: {csv_path}")

    with open(csv_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            bank_name = row.get("Bank Name", "").strip()
            swift_code = row.get("BIC", "").strip()

            if not bank_name or not swift_code:
                frappe.log_error(f"Skipping row: {row}", "Bank SWIFT Patch")
                continue

            bank = frappe.get_doc({
                "doctype": "Bank",
                "bank_name": bank_name,
                "swift_number": swift_code,
                "country":"Singapore"
            })

            # Cek jika sudah ada, update
            existing = frappe.db.exists("Bank", {"bank_name": bank_name})
            if existing:
                doc = frappe.get_doc("Bank", existing)
                doc.swift_number = swift_code
                doc.save(ignore_permissions=True)
            else:
                bank.insert(ignore_permissions=True)
                print("Add Bank", bank_name, swift_code )
    frappe.db.commit()
