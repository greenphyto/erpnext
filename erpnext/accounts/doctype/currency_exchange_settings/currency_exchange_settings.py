# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class CurrencyExchangeSettings(Document):
	def validate(self):
		self.set_parameters_and_result()
		if frappe.flags.in_test or frappe.flags.in_install or frappe.flags.in_setup_wizard:
			return
		response, value = self.validate_parameters()
		self.validate_result(response, value)

	def set_parameters_and_result(self):
		if self.service_provider == "exchangerate.host":
			self.set("result_key", [])
			self.set("req_params", [])

			self.api_endpoint = "https://api.exchangerate.host/convert"
			self.append("result_key", {"key": "result"})
			self.append("req_params", {"key": "date", "value": "{transaction_date}"})
			self.append("req_params", {"key": "from", "value": "{from_currency}"})
			self.append("req_params", {"key": "to", "value": "{to_currency}"})
		elif self.service_provider == "frankfurter.app":
			self.set("result_key", [])
			self.set("req_params", [])

			self.api_endpoint = "https://frankfurter.app/{transaction_date}"
			self.append("result_key", {"key": "rates"})
			self.append("result_key", {"key": "{to_currency}"})
			self.append("req_params", {"key": "base", "value": "{from_currency}"})
			self.append("req_params", {"key": "symbols", "value": "{to_currency}"})
		elif self.service_provider == "mas.gov.sg":
			self.set("result_key", [])
			self.set("req_params", [])

			self.api_endpoint = "https://eservices.mas.gov.sg/api/action/datastore/search.json"
			self.append("result_key", {"key": "result"})
			self.append("result_key", {"key": "records"})
			self.append("result_key", {"key": "{from_currency}_{to_currency}"})
			self.append("req_params", {"key": "resource_id", "value": "95932927-c8bc-4e7a-b484-68a66a24edfe"})
			self.append("req_params", {"key": "filters[end_of_day]", "value": "{transaction_date}"})
			self.append("req_params", {"key": "fields", "value": "{from_currency}_{to_currency}"})

	def validate_parameters(self):
		params = {}
		for row in self.req_params:
			params[row.key] = row.value.lower().format(
				transaction_date=nowdate(), to_currency="SGD", from_currency="USD"
			).lower()

		api_url = self.api_endpoint.format(
			transaction_date=nowdate(), to_currency="SGD", from_currency="USD"
		)

		try:
			response = requests.get(api_url, params=params)
		except requests.exceptions.RequestException as e:
			frappe.throw("Error: " + str(e))

		response.raise_for_status()
		value = response.json()

		return response, value

	def validate_result(self, response, value):
		try:
			
			for key in self.result_key:
				if  isinstance(value,dict):
					value = value[
					str(key.key.lower()).format(transaction_date=nowdate(), to_currency="SGD", from_currency="USD")
					]
				elif  isinstance(value,list):
					value = value[0][
					str(key.key.lower()).format(transaction_date=nowdate(), to_currency="SGD", from_currency="USD").lower()
					]	 
		except Exception:
			frappe.throw(_("Invalid result key. Response:") + " " + response.text)
		if not isinstance(value, (int, float,str)):
			frappe.throw(_("Returned exchange rate is neither integer not float."))

		self.url = response.url
