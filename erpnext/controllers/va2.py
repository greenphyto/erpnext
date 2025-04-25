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

def get_po_number(image_path):
	prompt = f"""
Extract data from image document given, get Purchase Order/P.O/PO from given document.
The name like PO000171/2025, PO1001123/2025, PO000100/2023, PO100072/2024
Just return the name only
	"""
	res = extract_invoice_data(image_path, prompt)

	return res

def get_item_detail(image_path, reference_item=[]):
	prompt = f"""
Extract item details from image document given, and return data like this format:
{
	json.dumps([
		{"item_code":"item1", "qty":2, "rate":20, "uom":"Unit", "currency":"USD"},
		{"item_code":"item2", "qty":10, "rate":12, "uom":"Kg", "currency":"USD"}
	])
}

reference item:
{
	json.dumps(reference_item)
}

hint:
1. Use reference item to matching with the invoice
2. Use "item_code" from reference as item_code key of the result
3. Return as JSON data without markdown format
4. if not found return []
"""
	res = extract_invoice_data(image_path, prompt)
	return res