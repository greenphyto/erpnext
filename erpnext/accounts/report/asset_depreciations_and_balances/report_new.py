# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import add_days, flt, formatdate


def execute(filters=None):
	filters.day_before_from_date = add_days(filters.from_date, -1)
	columns, data = get_columns(filters), get_data(filters)
	return columns, data


def get_data(filters):
	data = []

	asset_categories = get_asset_categories()
	asset_groups = get_asset_individual(filters)
	assets = get_assets(filters)

	asset_selects = frappe._dict()
	for asset in asset_groups:
		asset_selects[asset.name] = asset

	map_assets = frappe._dict()
	calculate_fields = [
		'cost_as_on_from_date',
		'accumulated_depreciation_as_on_from_date',
		'depreciation_eliminated_during_the_period',
		'depreciation_amount_during_the_period',
		'cost_of_scrapped_asset',
		'cost_of_sold_asset',
		'cost_of_new_purchase',
	]
	for asset in assets:
		category = asset["asset_category"]
		asset_select = asset_selects[asset.name]

		if category not in map_assets:
			map_assets[category] = {
				"assets":[asset]
			}
			for field in calculate_fields:
				asset[field] = flt(asset.get(field)) or flt(asset_select.get(field))
				map_assets[category][field] = asset.get(field)
		else:
			map_assets[category]['assets'].append(asset)
			for field in calculate_fields:
				asset[field] = flt(asset.get(field)) or flt(asset_select.get(field))
				map_assets[category][field] += asset.get(field)
		
		asset.cost_as_on_to_date = (
			flt(asset.cost_as_on_from_date)
			+ flt(asset.cost_of_new_purchase)
			- flt(asset.cost_of_sold_asset)
			- flt(asset.cost_of_scrapped_asset)
		)

		asset.accumulated_depreciation_as_on_to_date = (
			flt(asset.accumulated_depreciation_as_on_from_date)
			+ flt(asset.depreciation_amount_during_the_period)
			- flt(asset.depreciation_eliminated_during_the_period)
		)

		asset.net_asset_value_as_on_from_date = flt(asset.cost_as_on_from_date) - flt(
			asset.accumulated_depreciation_as_on_from_date
		)

		asset.net_asset_value_as_on_to_date = flt(asset.cost_as_on_to_date) - flt(
			asset.accumulated_depreciation_as_on_to_date
		)

	for asset_category in asset_categories:
		row = frappe._dict()
		category = asset_category.get("asset_category", "")
		# row.asset_category = asset_category

		assets = map_assets[category]
		for field in calculate_fields:
			row[field] = assets.get(field)			

		row.update(asset_category)
		
		row.cost_as_on_to_date = (
			flt(row.cost_as_on_from_date)
			+ flt(row.cost_of_new_purchase)
			- flt(row.cost_of_sold_asset)
			- flt(row.cost_of_scrapped_asset)
		)

		row.accumulated_depreciation_as_on_to_date = (
			flt(row.accumulated_depreciation_as_on_from_date)
			+ flt(row.depreciation_amount_during_the_period)
			- flt(row.depreciation_eliminated_during_the_period)
		)

		row.net_asset_value_as_on_from_date = flt(row.cost_as_on_from_date) - flt(
			row.accumulated_depreciation_as_on_from_date
		)

		row.net_asset_value_as_on_to_date = flt(row.cost_as_on_to_date) - flt(
			row.accumulated_depreciation_as_on_to_date
		)

		data.append(row)

		for asset in assets['assets']:
			child = frappe._dict(asset)
			child.asset_category = asset.name
			child.indent = 1
			data.append(child)

	return data

def get_asset_categories():
	return frappe.db.get_all("Asset Category", fields=['name as asset_category'])

def get_asset_individual(filters):
	return frappe.db.sql(
		"""
		SELECT asset_category, name,
			   ifnull(sum(case when purchase_date < %(from_date)s then
							   case when ifnull(disposal_date, 0) = 0 or disposal_date >= %(from_date)s then
									gross_purchase_amount
							   else
									0
							   end
						   else
								0
						   end), 0) as cost_as_on_from_date,
			   ifnull(sum(case when purchase_date >= %(from_date)s then
			   						gross_purchase_amount
			   				   else
			   				   		0
			   				   end), 0) as cost_of_new_purchase,
			   ifnull(sum(case when ifnull(disposal_date, 0) != 0
			   						and disposal_date >= %(from_date)s
			   						and disposal_date <= %(to_date)s then
							   case when status = "Sold" then
							   		gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as cost_of_sold_asset,
			   ifnull(sum(case when ifnull(disposal_date, 0) != 0
			   						and disposal_date >= %(from_date)s
			   						and disposal_date <= %(to_date)s then
							   case when status = "Scrapped" then
							   		gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as cost_of_scrapped_asset
		from `tabAsset`
		where docstatus=1 and company=%(company)s and purchase_date <= %(to_date)s
		group by name
	""",
		{"to_date": filters.to_date, "from_date": filters.from_date, "company": filters.company},
		as_dict=1,
	)


def get_assets(filters):
	return frappe.db.sql(
		"""
		SELECT results.asset_category, results.name,
			   sum(results.accumulated_depreciation_as_on_from_date) as accumulated_depreciation_as_on_from_date,
			   sum(results.depreciation_eliminated_during_the_period) as depreciation_eliminated_during_the_period,
			   sum(results.depreciation_amount_during_the_period) as depreciation_amount_during_the_period
		from (SELECT a.asset_category,a.name,
				   ifnull(sum(case when ds.schedule_date < %(from_date)s and (ifnull(a.disposal_date, 0) = 0 or a.disposal_date >= %(from_date)s) then
								   ds.depreciation_amount
							  else
								   0
							  end), 0) as accumulated_depreciation_as_on_from_date,
				   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0 and a.disposal_date >= %(from_date)s
										and a.disposal_date <= %(to_date)s and ds.schedule_date <= a.disposal_date then
								   ds.depreciation_amount
							  else
								   0
							  end), 0) as depreciation_eliminated_during_the_period,
				   ifnull(sum(case when ds.schedule_date >= %(from_date)s and ds.schedule_date <= %(to_date)s
										and (ifnull(a.disposal_date, 0) = 0 or ds.schedule_date <= a.disposal_date) then
								   ds.depreciation_amount
							  else
								   0
							  end), 0) as depreciation_amount_during_the_period
			from `tabAsset` a, `tabDepreciation Schedule` ds
			where a.docstatus=1 and a.company=%(company)s and a.purchase_date <= %(to_date)s and a.name = ds.parent and ifnull(ds.journal_entry, '') != ''
			group by a.name
			union
			SELECT a.asset_category,a.name,
				   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0 and (a.disposal_date < %(from_date)s or a.disposal_date > %(to_date)s) then
									0
							   else
									a.opening_accumulated_depreciation
							   end), 0) as accumulated_depreciation_as_on_from_date,
				   ifnull(sum(case when a.disposal_date >= %(from_date)s and a.disposal_date <= %(to_date)s then
								   a.opening_accumulated_depreciation
							  else
								   0
							  end), 0) as depreciation_eliminated_during_the_period,
				   0 as depreciation_amount_during_the_period
			from `tabAsset` a
			where a.docstatus=1 and a.company=%(company)s and a.purchase_date <= %(to_date)s
			group by a.name
			) as results
		group by results.name
		
		""",
		{"to_date": filters.to_date, "from_date": filters.from_date, "company": filters.company},
		as_dict=1,
	)


def get_columns(filters):
	return [
		{
			"label": _("Asset Category"),
			"fieldname": "asset_category",
			"fieldtype": "Link",
			"options": "Asset Category",
			"width": 120,
		},
		{
			"label": _("Cost as on") + " " + formatdate(filters.day_before_from_date),
			"fieldname": "cost_as_on_from_date",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Cost of New Purchase"),
			"fieldname": "cost_of_new_purchase",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Cost of Sold Asset"),
			"fieldname": "cost_of_sold_asset",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Cost of Scrapped Asset"),
			"fieldname": "cost_of_scrapped_asset",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Cost as on") + " " + formatdate(filters.to_date),
			"fieldname": "cost_as_on_to_date",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Accumulated Depreciation as on") + " " + formatdate(filters.day_before_from_date),
			"fieldname": "accumulated_depreciation_as_on_from_date",
			"fieldtype": "Currency",
			"width": 270,
		},
		{
			"label": _("Depreciation Amount during the period"),
			"fieldname": "depreciation_amount_during_the_period",
			"fieldtype": "Currency",
			"width": 240,
		},
		{
			"label": _("Depreciation Eliminated due to disposal of assets"),
			"fieldname": "depreciation_eliminated_during_the_period",
			"fieldtype": "Currency",
			"width": 300,
		},
		{
			"label": _("Accumulated Depreciation as on") + " " + formatdate(filters.to_date),
			"fieldname": "accumulated_depreciation_as_on_to_date",
			"fieldtype": "Currency",
			"width": 270,
		},
		{
			"label": _("Net Asset value as on") + " " + formatdate(filters.day_before_from_date),
			"fieldname": "net_asset_value_as_on_from_date",
			"fieldtype": "Currency",
			"width": 200,
		},
		{
			"label": _("Net Asset value as on") + " " + formatdate(filters.to_date),
			"fieldname": "net_asset_value_as_on_to_date",
			"fieldtype": "Currency",
			"width": 200,
		},
	]
