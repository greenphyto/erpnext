# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, requests, json
from frappe.model.document import Document
from urllib.parse import urljoin
from six import string_types
from frappe.model.document import Document
from frappe.utils import cint

class FOMSIntegrationSettings(Document):
	@frappe.whitelist()
	def get_raw_material(self):
		frappe.enqueue("erpnext.controllers.foms.get_raw_material", show_progress=True)
	
	@frappe.whitelist()
	def get_products(self):
		frappe.enqueue("erpnext.controllers.foms.get_products", show_progress=True)

def is_enable_integration():
	return cint(frappe.db.get_single_value('FOMS Integration Settings', "enable"))

def get_farm_id():
	farm_id = cint(frappe.db.get_single_value('FOMS Integration Settings', "farm_id"))
	return farm_id

class FomsAPI():
	# API
	def __init__(self, settings=None):
		self.settings = settings or frappe.get_single("FOMS Integration Settings")
		self.token = ""
		self.init_request()

	def init_request(self):
		self.session = requests.Session()
		self.update_header({
			'accept': 'application/json',
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
		if req == "POST":
			res = self.session.post(url, data=data, params=params)
		else:
			res = self.session.get(url, data=data, params=params)

		if frappe.flags.in_test:
			print(data)
			print(res.status_code)
			print(res.text)

		result =  res.json()
		if "error" in result and result['error']:
			print("ERROR: ", result['error'])

		return result.get("result") or {}
	
	def get_all_customer(self):
		res = self.req("GET", "/Customer/GetAllCustomer", params={
			"MaxResultCount":999
		})

		return res
	
	def create_or_update_supplier(self, data={}):
		data['isFromERP'] = True

		res = self.req("POST", "/Supplier/CreateOrUpdateSupplier", data= json.dumps(data) )

		return res

	def create_or_update_customer(self, data={}):
		data['isFromERP'] = True

		res = self.req("POST", "/Customer/CreateOrUpdateCustomer", data= json.dumps(data) )

		return res
	
	def get_raw_material(self, farm_id):
		params = {
			"FarmId":farm_id,
			"MaxResultCount":99999
		}
		res = self.req("GET", "/RawMaterial/GetAllRawMaterial", params=params )
		return res.get("rawMaterialFinishList") or {}
	
	def get_products(self, farm_id):
		params = {
			"FarmId":farm_id,
			"MaxResultCount":99999
		}
		res = self.req("GET", "/Product/GetAllProducts", params=params )
		return res.get("productFinishedList") or {}
