import frappe

def execute():
    frappe.db.sql("""
        update tabToDo set status="Planned" where status = "Open"
    """)

    frappe.db.sql("""
        update tabToDo set status="Completed" where status = "Closed"
    """)
from frappe.utils.user import get_users_with_role

"""
bench --site smart-fm.arber.ai execute erpnext.patches.v14_0.update_todo_task.update_force_bm_role
"""
def update_force_bm_role():
    bm_other_role = ['Building Management (Manager)', 'Building Management (Team)', 'Building Management (Master)']
    users = []
    for role in bm_other_role:
        users += get_users_with_role(role)
    
    users = tuple(users)
    for user in users:
        doc = frappe.get_doc("User", user)
        add = True
        is_bm_user = True
        for d in doc.get("roles"):
            if d.role in bm_other_role:
                is_bm_user = True
                
            if d.role == 'Building Management':
                add = False
        
        if is_bm_user and add:
            print("Add BM to ", doc.name)
            row = doc.append("roles")
            row.role = "Building Management"
            doc.save()

