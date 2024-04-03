import frappe

# bench --site erp.greenphyto.com execute erpnext.patches.v14_0.update_gl_entry_against_column.update_gl_entry_against_account

def update_gl_entry_against_account():
    update_against_account = """
        UPDATE
            `tabGL Entry`
        SET 
            against_account = against
        WHERE
            against like "%GPL%"
    """

    update_against_party = """
        UPDATE
            `tabGL Entry`
        SET 
            against_party = against
        WHERE
            against not like "%GPL%"
            AND against is not null
    """

    frappe.db.sql(update_against_account)
    frappe.db.sql(update_against_party)

def split_account_name():
    frappe.db.sql("""
    update
        `tabGL Entry` gl
                LEFT JOIN
        `tabAccount` a ON a.name = gl.account
    set gl.account_name = CONCAT(a.account_name, " - GPL")
    """, as_dict=1)