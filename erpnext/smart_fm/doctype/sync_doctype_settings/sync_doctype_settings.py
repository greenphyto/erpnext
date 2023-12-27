# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, requests, json
from frappe.model.document import Document
from urllib.parse import urljoin
from six import string_types

class SyncDoctypeSettings(Document):
	def get_login(self):
		pass

class SyncAPI():
	def __init__(self, settings=None):
		self.settings = settings or frappe.get_single("Sync Doctype Settings")
		self.init_request()

	def init_request(self):
		self.session = requests.Session()

	def get_url(self, method=""):
		url = urljoin(self.settings.origin_site, f"/api/method/{method}")
		return url
	
	def get_login(self):
		if self.session.cookies.get("user_id"):
			print(26)
			return
		
		url = self.get_url("login")
		res = self.session.post(url, data={
			"usr": self.settings.user,
			"pwd": self.settings.get_password("password"),
		})

		data = res.json()
		return data
	
	def req(self, req="POST", method="", data={}):
		url = self.get_url(method)
		self.get_login()
		if req == "POST":
			res = self.session.post(url, data=data)
		else:
			res = self.session.get(url, data=data)

		result =  res.json()

		return result.get("message")

	
	def get_pending_log(self):
		res = self.req("GET", "frappe.core.doctype.sync_log.sync_log.get_pending_log")
		return res

	def set_success(self, log_name):
		logs = []
		if isinstance(log_name, string_types):
			logs = [log_name]
		else:
			logs = log_name

		res = self.req("POST", "frappe.core.doctype.sync_log.sync_log.update_success", {"logs":json.dumps(logs)})
		return res
	
	def get_updates(self):
		# get update from every pending logs
		pass
