import datetime
import frappe
from frappe.utils import get_datetime, get_url
from frappe.api import get_social_login_providers
def get_context(context):
	expires = get_datetime() + datetime.timedelta(minutes=10)
	redirect = frappe.local.form_dict.get("redirect_to")
	provider = frappe.local.form_dict.get("provider")
	frappe.local.cookie_manager.set_cookie("redirect_to", redirect, expires=expires)
	home_page = get_url()
	context.home = home_page
	data = get_social_login_providers(home_page) or []
	for d in data:
		if not provider:
			context.link = d.get("auth_url")
			break
			
		if d.get("provider_name") == provider:
			context.link = data.get("auth_url")