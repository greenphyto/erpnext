import frappe


def execute():
	frappe.db.sql(
		"""
		UPDATE `tabItem`
		SET rnd_item = 1
		WHERE item_code IN %(item_codes)s
		""",
		{
			"item_codes": (
				"RM-SD-ABS",
				"RM-SD-AUD",
				"RM-SD-BAS",
				"RM-SD-BER",
				"RM-SD-BL",
				"RM-SD-BLA",
				"RM-SD-BLK",
				"RM-SD-BRO",
				"RM-SD-CAI",
				"RM-SD-CHG",
				"RM-SD-CLL",
				"RM-SD-CRI",
				"RM-SD-DIL",
				"RM-SD-DUE",
				"RM-SD-DWA",
				"RM-SD-EMI",
				"RM-SD-EXM",
				"RM-SD-FDW",
				"RM-SD-FIG",
				"RM-SD-FSC",
				"RM-SD-GAR",
				"RM-SD-GLO",
				"RM-SD-GOA",
				"RM-SD-GRA",
				"RM-SD-HYD",
				"RM-SD-ITA",
				"RM-SD-JT",
				"RM-SD-MAG",
				"RM-SD-MAR",
				"RM-SD-MIN",
				"RM-SD-MIZ",
				"RM-SD-RAA",
				"RM-SD-RAB",
				"RM-SD-RAC",
				"RM-SD-RAD",
				"RM-SD-RBA",
				"RM-SD-ROA",
				"RM-SD-ROM",
				"RM-SD-RRA",
				"RM-SD-RUB",
				"RM-SD-SCR",
				"RM-SD-SUA",
				"RM-SD-TAS",
				"RM-SD-TAT",
				"RM-SD-TB",
				"RM-SD-TIE",
				"RM-SD-VIO",
				"RM-SD-VOL",
				"RM-SD-WAS",
				"RM-SD-YEL",
			)
		},
	)
