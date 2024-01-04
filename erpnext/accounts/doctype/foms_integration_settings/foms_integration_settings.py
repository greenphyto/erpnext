# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, requests, json
from frappe.model.document import Document
from urllib.parse import urljoin
from six import string_types
from frappe.model.document import Document

class FOMSIntegrationSettings(Document):
	pass

class FomsAPI():
	# API
	def __init__(self, settings=None):
		self.settings = settings or frappe.get_single("FOMS Integration Settings")
		self.token = ""
		self.init_request()

	def init_request(self):
		self.session = requests.Session()
		self.update_header({
			'accept': 'text/plain',
			'Content-Type': 'application/json-patch+json',
		})

	def update_header(self, header):
		self.session.headers.update(header)

	def get_url(self, method=""):
		url = urljoin(self.settings.foms_url, "api"+method)
		return url
	
	def get_login(self):
		if self.token:
			return
		
		url = self.get_url("/TokenAuth/Authenticate")

		res = self.session.post(url, data=json.dumps({
			"userNameOrEmailAddress": self.settings.user,
			"password": self.settings.get_password("password"),
			"rememberClient":True
		}))

		if res.status_code == 200:
			data = res.json()
			if data.get("result") and data['result'].get("accessToken"):
				self.token = f"Bearer {data['result']['accessToken']}"
				self.update_header({
					"Authorization": self.token
				})

			return data
	
	def req(self, req="POST", method="", data={}, params={}):
		url = self.get_url(method)
		self.get_login()
		print(url)
		if req == "POST":
			res = self.session.post(url, data=data, params=params)
		else:
			res = self.session.get(url, data=data, params=params)

		print(res.status_code)
		result =  res.json()

		return result.get("result")
	
	def get_all_customer(self):
		res = self.req("GET", "/Customer/GetAllCustomer", params={
			"MaxResultCount":999
		})

		return res
