import frappe, os

# change site name and sites path
SITE_NAME = "test5"
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"

# 1. change your python path to frappe's env 

# 2. prepare your lunch.json for VSCode
# change the "program" of debug_script 
"""
{
    "name": "Bench Execute Function",
    "type": "debugpy",
    "request": "launch",
    "program": "/workspace/development/gp-frappe-bench/apps/erpnext/erpnext/debug_script.py",
    "console": "integratedTerminal",
    "justMyCode": false
}
"""

# 3. and run debug on sidebar

frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
frappe.connect()
file_path = "/workspace/development/gp-frappe-bench/apps/erpnext/erpnext/test_script.py"
if os.path.exists(file_path):
    from erpnext.test_script import execute
    execute()
else:
    print("Warning: test_script.py not exists")
frappe.destroy()
