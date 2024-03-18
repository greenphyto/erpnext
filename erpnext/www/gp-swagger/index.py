from frappe.sessions import get_csrf_token
def get_context(context):
    context.token = get_csrf_token()