import os, json
import numpy as np
from vision_agent.tools import *
from vision_agent.tools.planner_tools import judge_od_results
from typing import *
from pillow_heif import register_heif_opener
register_heif_opener()
import vision_agent as va
from vision_agent.tools import register_tool
import frappe
"""
USING DEEPSEEK
"""

def extract_invoice_data2(image_path: str, item_context={}, customer_context={}, email_sender=""):
	"""
	Extracts the specified invoice fields as JSON from the given invoice image using 'document_qa'.
	
	Parameters:
		image_path (str): Path to the invoice image file.
	
	Returns:
		str: A JSON string with the keys:
			 - company_name
			 - items (list of {description, qty, uom})
			 - shipping_address
			 - delivery_date
	"""
	from vision_agent.tools import load_image, document_qa
	result_json = ""
	# export vision-agent
	os.environ['VISION_AGENT_API_KEY'] = frappe.conf.vision_agent_token
	os.environ['OPENAI_API_KEY'] = frappe.conf.deepseek_token
	
	# Step 2: Load the invoice image
	image = load_image(image_path)

	# Step 3: Prepare the JSON prompt
	json_prompt = f"""
Email sender:{email_sender},
Extract and matching the items folowing this data: {item_context},
and customer following this data: {customer_context},
and packed to this raw JSON format (not .md format):
{ json.dumps({
	"company_name": "name of the company",
	"items": [
		{
			"item_code":"Item code like PR-XX-XXX",
			"description": "item description",
			"qty": "quantity",
			"uom": "unit of measure"
		}
	],
	"shipping_address": "complete shipping address",
	"delivery_date": "delivery date with format YYYY-MM-DD"
}) }
hint: 
1. if None use empty json string ""
2. the header detail is the customer code of ours
3. customer code can match by email sender
4. priorities item with no dash number like "PR-AV-KL".
	"""

	# Step 4: Use document_qa to extract the data
	print(json_prompt)
	result_json = document_qa(json_prompt, image) or {}

	res = {}
	try:
		res = json.loads(result_json)
	except Exception as e:
		error = e
		print("ERROR", error)
	return res

def extract_invoice_data(image_path: str, prompt: str):
	"""
	Extracts the specified invoice fields as JSON from the given invoice image using 'document_qa'.
	
	Parameters:
		image_path (str): Path to the invoice image file.
	
	Returns:
		str: A JSON string with the keys:
			 - company_name
			 - items (list of {description, qty, uom})
			 - shipping_address
			 - delivery_date
	"""
	from vision_agent.tools import load_image, document_qa
	os.environ['VISION_AGENT_API_KEY'] = frappe.conf.vision_agent_token
	os.environ['OPENAI_API_KEY'] = frappe.conf.deepseek_token
	result = ""
	image = load_image(image_path)
	result = document_qa(prompt, image) or {}
	result_json = {
		"result":result
	}
	return result_json

def get_inv_data(image_path, reference_item):
	pass

def get_po_number(image_path):
	prompt = f"""
Extract the Purchase Order number from the given document. The PO number format could be:
- PO000171/2025
- PO1001123/2025
- P0000171/2025 (with or without the "O" after "P")
- PO100072/2024
- Or other similar variations where the number may start with "P", "PO", or a similar pattern.

Return only the PO number(s) found in the document, in a clean format without any additional explanation, text, or markdown. If multiple PO numbers are found, return them as a list of strings.

If no PO numbers are found, return an empty list: []
	"""
	res = extract_invoice_data(image_path, prompt)

	return res

def get_item_detail(image_path, reference_item=[]):
	prompt = """
Extract item details from the provided invoice image and match them with the given Reference Item list.

Your task:
1. Use the Reference Item list to match the item descriptions or names found in the invoice image. Supplier item names may differ, so match them as best as possible based on semantic similarity or known aliases.
2. Return a list of matched items in the following JSON format (no markdown):
   [
     {"item_code": "from Reference Item", "qty": ..., "rate": ..., "uom": "...", "currency": "..."},
     ...
   ]
3. Use the "item_code" from the Reference Item for each matched item.
4. If no items match, return an empty list: []

Notes:
- Invoice images may use different item names or terms — do not rely on exact string match.
- Focus on meaning, context, quantity, unit, and rate when matching.
- Always return array in JSON string format, no markdown, no explanations.

Reference Item:
"""+json.dumps(reference_item, indent=2)

	# res = extract_invoice_data(image_path, prompt)
	res = """ {'result': '[{"item_code": "Waterflow Prototype 2", "qty": 2.0, "rate": 2200.0, "uom": "unit S", "currency": "SGD"}]'} """
	result = []

	try:
		start_index = res.find('[') 
		end_index = res.find(']') + 1 

		json_str = res[start_index:end_index]

		result = json.loads(json_str)
		
	except:
		return result
		
	return result