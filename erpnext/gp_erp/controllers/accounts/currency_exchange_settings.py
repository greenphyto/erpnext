import frappe
from frappe import _
from frappe.utils import nowdate
import requests

from erpnext.accounts.doctype.currency_exchange_settings.currency_exchange_settings import CurrencyExchangeSettings


class CurrencyExchangeSettingsGP(CurrencyExchangeSettings):
    def set_default_fields(self):
        if self.service_provider == "frankfurter":
            self.set("result_key", [])
            self.set("req_params", [])

            self.api_endpoint = "https://api.frankfurter.dev/v1/latest?base=${from_currency}&symbols=${to_currency}"
            self.append("result_key", {"key": "{to_currency}"})
            self.append("req_params", {"key": "base", "value": "{from_currency}"})
            self.append("req_params", {"key": "symbols", "value": "{to_currency}"})
        elif self.service_provider == "mas.gov.sg":
            self.set("result_key", [])

            self.api_endpoint = "https://eservices.mas.gov.sg/apimg-gw/server/monthly_statistical_bulletin_non610ora/exchange_rates_end_of_period_daily/views/exchange_rates_end_of_period_daily"
            self.append("result_key", {"key": "elements"})
            self.append("result_key", {"key": "{from_currency}_{to_currency}"})

    def validate_parameters(self):
        params = {}
        for row in self.req_params:
            params[row.key] = row.value.format(
                transaction_date=nowdate(), to_currency="SGD", from_currency="USD"
            )

        headers = {
            "accept": "application/json"
        }
        for row in self.header_params:
            headers[row.key] = row.value.lower().format(
                transaction_date=nowdate(), to_currency="SGD", from_currency="USD"
            ).lower()

        try:
            response = requests.get(self.api_endpoint, params=params, headers=headers)
        except requests.exceptions.RequestException as e:
            frappe.throw("Error: " + str(e))
        self.validate_result(response, response.json())

    def validate_result(self, response, value):
        try:
            if value.get("name") and value['name'] == "exchange_rates_end_of_period_daily":
                return
            for key in self.result_key:
                if isinstance(value, dict):
                    value = value[
                        str(key.key.lower()).format(transaction_date=nowdate(), to_currency="SGD", from_currency="USD")
                    ]
                else:
                    value = value[0]
        except Exception:
            frappe.throw(_("Invalid result key. Response:") + " " + response.text)
        if not isinstance(value, (int, float, str)):
            frappe.throw(_("Returned exchange rate is neither integer not float."))
        self.url = response.url
