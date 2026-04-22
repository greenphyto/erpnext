# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# GPL v3 License. See license.txt

import click
from erpnext.commands.hello import hello
from erpnext.commands.create_custom import create_custom


def call_command(cmd, context):
	return click.Context(cmd, obj=context).forward(cmd)


commands = [hello, create_custom]
