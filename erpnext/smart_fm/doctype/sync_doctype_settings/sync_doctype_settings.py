# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, requests
from frappe.model.document import Document
from urllib.parse import urljoin

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
		url = self.get_url("login")
		res = self.session.post(url, data={
			"usr": self.settings.api_key,
			"pwd": self.settings.get_password("api_secret"),
		})

		data = res.json()
		return data