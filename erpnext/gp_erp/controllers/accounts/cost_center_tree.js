frappe.treeview_settings["Cost Center"] = {
	get_tree_nodes: function(doc) { ... },
	// GP: node_onload sets abbreviation from parent
};

// GP: node_onload for auto-fill abbreviation
$.extend(frappe.treeview_settings["Cost Center"], {
	node_onload: function(dialog) {
		setTimeout(() => {
			var data = dialog.get_values(1);
			dialog.set_value("abbreviation", data.parent_cost_center);
		}, 500);
	}
});
