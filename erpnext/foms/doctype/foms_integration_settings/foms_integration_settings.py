# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, requests, json, copy
from frappe.model.document import Document
from urllib.parse import urljoin
from six import string_types
from frappe.model.document import Document
from frappe.utils import cint
from frappe.core.doctype.sync_log.sync_log import update_success, update_error

class FOMSIntegrationSettings(Document):
	@frappe.whitelist()
	def get_raw_material(self):
		frappe.msgprint("Get raw material running..")
		frappe.enqueue("erpnext.controllers.foms.get_raw_material", show_progress=True)
	
	@frappe.whitelist()
	def get_products(self):
		frappe.msgprint("Get products running..")
		frappe.enqueue("erpnext.controllers.foms.get_products", show_progress=True)

	@frappe.whitelist()
	def get_recipe(self):
		frappe.msgprint("Get recipe running..")
		frappe.enqueue("erpnext.controllers.foms.get_recipe", show_progress=True)

	@frappe.whitelist()
	def sync_supplier(self):
		frappe.msgprint("Sync supplier running..")
		frappe.enqueue("erpnext.controllers.foms.sync_all_supplier", show_progress=True)

	@frappe.whitelist()
	def sync_customer(self):
		frappe.msgprint("Sync customer running..")
		frappe.enqueue("erpnext.controllers.foms.sync_all_customer", show_progress=True)

	@frappe.whitelist()
	def sync_warehouse(self):
		frappe.msgprint("Sync warehouse running..")
		frappe.enqueue("erpnext.controllers.foms.sync_all_warehouse", show_progress=True)

	@frappe.whitelist()
	def get_packaging(self):
		frappe.msgprint("Get packaging running..")
		frappe.enqueue("erpnext.controllers.foms.get_packaging", show_progress=True)

	@frappe.whitelist()
	def get_batch(self):
		frappe.msgprint("Get batch running..")
		frappe.enqueue("erpnext.controllers.foms.get_batch", show_progress=True)


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
			'Content-Type': 'application/json',
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

	def convert_data(self, data):
		def fix_data(data):
			if type(data) is list:
				for i, e in enumerate(data):
					if e is None:
						data[i] = ''
					else:
						fix_data(e)

			elif type(data) is dict:
				for k, v in data.items():
					if v is None:
						data[k] = ''
					else:
						fix_data(v)
		fix_data(data)
		res = json.dumps(data, default=str)
		return res
	
	def req(self, req="POST", method="", data={}, params={}):
		url = self.get_url(method)
		self.get_login()
		if req == "POST":
			res = self.session.post(url, data=data, params=params)
		elif req == "DELETE":
			res = self.session.delete(url, data=data, params=params)
		else:
			res = self.session.get(url, data=data, params=params)

		self.last_result = res
		self.request_detail = {
			"host":self.settings.foms_url,
			"url":url,
			"method":req
		}

		try:
			self.request_detail['data'] = json.loads(data)
		except:
			pass

		self.update_log()

		if frappe.flags.in_test:
			print(data)
			print(res.status_code)
			print(res.text)

		try:
			result =  res.json()
			if "error" in result and result['error']:
				print("ERROR: ", result['error'])

			return result.get("result") or {}
		except:
			result =  res.text
			return False

	
	def update_log(self):
		if not hasattr(self, "log") or not self.log:
			return
		
		if self.last_result.status_code == 200:
			update_success([self.log.name])
		else:
			update_error([{
				"log":self.log.name,
				"error":self.last_result.text,
				"status_code":self.last_result.status_code,
				"request":self.request_detail
			}])
	
	def get_all_customer(self):
		res = self.req("GET", "/Customer/GetAllCustomer", params={
			"MaxResultCount":999
		})

		return res
	
	def create_or_update_supplier(self, data={}):
		data['isFromERP'] = True

		data = self.convert_data(data)
		res = self.req("POST", "/Supplier/CreateOrUpdateSupplier", data= data )

		return res

	def create_or_update_customer(self, data={}):
		data['isFromERP'] = True

		data = self.convert_data(data)
		res = self.req("POST", "/Customer/CreateOrUpdateCustomer", data= data )

		return res
	
	def get_raw_material(self, farm_id, reff_no=""):
		params = {
			"FarmId":farm_id,
			"MaxResultCount":99999,
			"RawMaterialRefNo": reff_no
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
	
	def get_packaging(self, product_id):
		params = {
			"ProductId":product_id,
			"MaxResultCount":99999
		}
		res = self.req("GET", "/userportal/CustomerOrder/GetPackageList", params=params )
		return res

	def get_recipe(self, farm_id, product_id):
		params = {
			"FarmId":farm_id,
			"ProductId": product_id,
		}
		res = self.req("GET", "/Recipe/GetRecipeByProductId", params=params )
		return res
	
	def get_product_process(self, farm_id, product_id):
		params = {
			"FarmId":farm_id,
			"ProductId": product_id,
		}
		res = self.req("GET", "/Product/GetProductProcessByProductID", params=params )
		return res
	
	def get_product_list_for_recipe(self, farm_id):
		params = {
			"FarmId":farm_id,
		}
		res = self.req("GET", "/Recipe/GetProductList", params=params )
		return res

	def get_work_order_list(self, farm_id, work_order=""):
		params = {
			"FarmId":farm_id,
			"workOrderNo":work_order
		}
		res = self.req("GET", "/userportal/CommonLookup/GetWorkOrderList", params=params )
		return res

	def get_work_order_detail(self, farm_id, work_order=""):
		params = {
			"FarmId":farm_id,
			"workOrderId":work_order
		}
		res = self.req("GET", "/userportal/Operation/GetOperationTimeLineByWorkOrderId", params=params)
		return res

	def update_warehouse(self, data):
		data = self.convert_data(data)
		res = self.req("POST", "/Warehouse/CreateOrUpdateWarehouse", data=data )
		return res

	def update_raw_material_receipt(self, data):
		data = self.convert_data(data)
		res = self.req("POST", "/userportal/ERPNextIntegration/RawMaterialReceipt", data=data )
		return res

	def get_all_warehouse(self, farm_id):
		params = {
			"FarmId":farm_id,
			"MaxResultCount":9999
		}
		res = self.req("GET", "/Warehouse/GetAllWarehouses", params=params )
		return res
	
	def get_all_supplier(self, farm_id):
		params = {
			"FarmId":farm_id,
			"MaxResultCount":9999
		}
		res = self.req("GET", "/Supplier/GetAll", params=params )
		return res

	def get_all_batch(self):
		params = {
			"MaxResultCount":9999
		}
		res = self.req("GET", "/userportal/RawMaterialUP/GetAllRawMaterialBatch", params=params )
		return res
	
	def get_all_customer(self, farm_id):
		params = {
			"FarmId":farm_id,
			"MaxResultCount":9999
		}
		res = self.req("GET", "/Customer/GetAllCustomer", params=params )
		return res
	
	def create_customer_order(self, data):
		data = self.convert_data(data)
		res = self.req("POST", "/userportal/CustomerOrder/CreateOrUpdateCustomerOrder", data=data)

		return res
	
	def update_raw_material_batch_qty(self, data):
		data = self.convert_data(data)
		res = self.req("POST", "/userportal/RawMaterialUP/CreateOrUpdateRawMaterialBatch", data=data)

		return res
	
	def post_scrap_issue(self, data):
		res = self.req("POST", "/userportal/RawMaterialUP/UpdateRawMaterialStatusToExpired", params=data)
		return res

	def get_workorder_detail(self, lot_id):
		params = {
			"workOrderId":lot_id
		}
		res = self.req("GET", "/userportal/Planning/GetWorkOrderPlanningOutcomeList", params=params)
		return res

	def update_foms_department(self, data):
		data = self.convert_data(data)
		res = self.req("POST", "/userportal/CustomerOrder/CreateOrUpdateDepartment", data=data)

		return res
	
	def create_delivery_note(self, data):
		data = self.convert_data(data)
		res = self.req("POST", "/userportal/ERPNextIntegration/CreateOrUpdateDeliveryOrder", data=data)

		return res
	
	def delete_customer(self, id):
		params = {
			"id": cint(id)
		}
		res = self.req("DELETE", "/Customer/DeleteCustomer", params=params)
		return res
	
	def delete_supplier(self, id):
		params = {
			"id": cint(id)
		}
		res = self.req("DELETE", "/Supplier/Delete", params=params)
		return res
	
	def delete_warehouse(self, id):
		params = {
			"id": cint(id)
		}
		res = self.req("DELETE", "/Warehouse/DeleteWarehouse", params=params)
		return res

	def cancel_sales_order(self, id):
		id = cint(id)
		res = self.req("DELETE", f"/userportal/CustomerOrder/CancelSaleOrder?SaleOrderId={id}&IsOnlyThisOne=true")
		return res

	
"""
TODO:
update batch qty to userportal/RawMaterialUP/CreateOrUpdateRawMaterialBatch
{
  "rawMaterialId": 72,
  "batchRefNo": "RM-SD-KOM-BN00001",
  "quantityUOM": "g",
  "warehouseName": "Warehouse",
  "warehouseId": 4,
  "warehouseRefId": "WH-SG-00001",
  "id": 236,
  "quantity": 7,
  "FarmId": 15
}
"""

