# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CleaningArea(Document):
	def validate(self):
		self.make_level_summary()

	def make_level_summary(self):
		levels = []
		for d in [1,2,3,4,5]:
			d = str(d)
			level = "level_" + d
			enable = self.get(level)
			if enable:
				levels.append(d)
		
		self.level = "Level "+", ".join(levels)

