from openai import OpenAI
import frappe, json
from erpnext.controllers.erp import get_item_context, get_customer_context

class deepseekAI():
	def __init__(self):
		self.client = OpenAI(api_key=frappe.conf.deepseek_token, base_url="https://api.deepseek.com")

	def send_context(self, message, context):
		response = self.client.chat.completions.create(
			model="deepseek-chat",
			messages=[
				{"role": "system", "content": context},
				{"role": "user", "content": message},
			],
			stream=False
		)

		res = response.choices[0].message.content

		return res
	
def process_email_supplier(doc, method=""):
	# filter
	if not doc.communication_medium == "Email":
		return
	if not frappe.conf.invoice_email or frappe.conf.invoice_email not in doc.recipients:
		return
	
	item_context = get_item_context()
	customer_context = get_customer_context()
	example = {
		"items": [
			{
				"PR-AV-KL": {
					"qty": 2
				}
			}
		],
		"customer":"Arber Pte. Ltd.",
		"delivery_date":"2025-01-01"
	}
	context = f"""you are AI agent to read item requested from supplier in email to ERP available item. 
Extract the available customer and get the delivery date.
The Item: {item_context}. 
The Customer: {customer_context}.
return as json like this format: {example}"""
	app = deepseekAI()
	res = app.send_context(
		message=doc.content,
		context=context
	)

	res = res.replace("```json", "").replace("```", "").strip()
	res = json.loads(res)

	return res
