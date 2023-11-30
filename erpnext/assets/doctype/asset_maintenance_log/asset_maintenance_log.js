// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Maintenance Log', {
	refresh: function(frm){
		frm.set_query('task', function(doc) {
			if (!doc.asset_maintenance) frappe.throw(__("Please set Asset Maintenance!"));
			return {
				query: "erpnext.assets.doctype.asset_maintenance_log.asset_maintenance_log.get_maintenance_tasks",
				filters: {
					'asset_maintenance': doc.asset_maintenance
				}
			};
		});

		frm.set_query("asset_maintenance", function(doc) {
			return {
				query: "erpnext.assets.doctype.asset_maintenance_log.asset_maintenance_log.filter_asset_maintenance",
			};
		});
	}
});
