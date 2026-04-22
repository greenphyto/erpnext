# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# GPL v3 License. See license.txt

import os
import re
import click
import frappe
from frappe.utils import cstr


@click.command("create-custom")
@click.option("--doctype", required=True, help="Doctype name to create custom class for")
@click.pass_context
def create_custom(ctx, doctype):
	"""
	Create a custom class file for a doctype and register it in hooks.py
	
	Usage: 
		bench --site <site_name> create-custom --doctype "Sales Invoice"
		bench --site site1.local create-custom --doctype "Purchase Order"
	
	This command will:
		1. Create a custom class file in the doctype folder
		2. Automatically update hooks.py with override_doctype_class entry
		3. Use proper inheritance from the original doctype class
	"""
	# Get site from context
	site = None
	if ctx.obj and "sites" in ctx.obj:
		sites = ctx.obj.get("sites", [])
		if sites:
			site = sites[0]
	
	if not site:
		click.echo(click.style("Error: No site specified. Please specify a site using --site flag", fg="red"))
		click.echo("\nUsage: bench --site <site_name> create-custom --doctype \"Doctype Name\"")
		click.echo("\nExample:")
		click.echo("  bench --site site1.local create-custom --doctype \"Sales Invoice\"")
		return
	
	frappe.init(site=site)
	frappe.connect()
	
	try:
		# Get doctype details from database
		doctype_info = frappe.db.get_value(
			"DocType", 
			doctype, 
			["name", "module", "custom"], 
			as_dict=True
		)
		
		if not doctype_info:
			click.echo(click.style(f"Error: Doctype '{doctype}' not found!", fg="red"))
			return
		
		if doctype_info.custom:
			click.echo(click.style(f"Error: '{doctype}' is a custom doctype. Custom classes are only for standard doctypes.", fg="red"))
			return
		
		module = doctype_info.module
		doctype_name = doctype_info.name
		
		# Convert doctype name to folder name (lowercase with underscores)
		folder_name = frappe.scrub(doctype_name)
		class_name = "".join([word.capitalize() for word in folder_name.split("_")])
		
		# Get module path
		module_path = frappe.get_module_path(module)
		doctype_folder = os.path.join(module_path, "doctype", folder_name)
		
		# Check if doctype folder exists
		if not os.path.exists(doctype_folder):
			click.echo(click.style(f"Error: Doctype folder not found at {doctype_folder}", fg="red"))
			return
		
		# Create custom file path
		custom_file_name = f"{folder_name}_custom.py"
		custom_file_path = os.path.join(doctype_folder, custom_file_name)
		
		# Check if custom file already exists
		if os.path.exists(custom_file_path):
			click.echo(click.style(f"Error: Custom file already exists at {custom_file_path}", fg="yellow"))
			return
		
		# Generate custom class content
		content = generate_custom_class_content(folder_name, class_name)
		
		# Write custom file
		with open(custom_file_path, "w") as f:
			f.write(content)
		
		click.echo(click.style(f"✓ Created custom file: {custom_file_path}", fg="green"))
		
		# Update hooks.py
		update_hooks_py(doctype_name, module, folder_name, class_name)
		
		click.echo(click.style(f"✓ Updated hooks.py with override_doctype_class entry", fg="green"))
		click.echo(click.style(f"\nCustom class created successfully!", fg="green", bold=True))
		click.echo(f"\nFile: {custom_file_path}")
		click.echo(f"Class: {class_name}Custom")
		
	except Exception as e:
		click.echo(click.style(f"Error: {str(e)}", fg="red"))
		import traceback
		click.echo(traceback.format_exc())
	finally:
		frappe.destroy()


def generate_custom_class_content(folder_name, class_name):
	"""Generate the content for custom class file"""
	content = f'''from .{folder_name} import {class_name}
import frappe

#Important!: always use super() to override standard function

class {class_name}Custom({class_name}):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
	def validate(self):
		super().validate()
		# Add your custom validation logic here
		pass
'''
	return content


def update_hooks_py(doctype_name, module, folder_name, class_name):
	"""Update hooks.py to add override_doctype_class entry"""
	# Get hooks.py path
	app_path = frappe.get_app_path("erpnext")
	hooks_path = os.path.join(app_path, "hooks.py")
	
	# Read hooks.py
	with open(hooks_path, "r") as f:
		content = f.read()
	
	# Generate the path string
	module_lower = frappe.scrub(module)
	custom_path = f'"{doctype_name}": "erpnext.{module_lower}.doctype.{folder_name}.{folder_name}_custom.{class_name}Custom"'
	
	# Check if override_doctype_class exists
	if "override_doctype_class" in content:
		# Find the override_doctype_class dictionary
		pattern = r'override_doctype_class\s*=\s*\{([^}]*)\}'
		match = re.search(pattern, content, re.DOTALL)
		
		if match:
			dict_content = match.group(1)
			
			# Check if doctype already exists in the dict
			if f'"{doctype_name}"' in dict_content:
				click.echo(click.style(f"Warning: '{doctype_name}' already exists in override_doctype_class", fg="yellow"))
				return
			
			# Add new entry (before closing brace)
			# Find the last entry and add comma if needed
			dict_content_stripped = dict_content.strip()
			if dict_content_stripped and not dict_content_stripped.endswith(','):
				new_dict_content = dict_content.rstrip() + ',\n    ' + custom_path + ',\n'
			else:
				new_dict_content = dict_content.rstrip() + '\n    ' + custom_path + ',\n'
			
			# Replace in content
			new_override = f'override_doctype_class = {{\n{new_dict_content}}}'
			content = re.sub(pattern, new_override, content, flags=re.DOTALL)
	else:
		# Add override_doctype_class at the end of file
		override_block = f'\noverride_doctype_class = {{\n    {custom_path},\n}}\n'
		content += override_block
	
	# Write back to hooks.py
	with open(hooks_path, "w") as f:
		f.write(content)
