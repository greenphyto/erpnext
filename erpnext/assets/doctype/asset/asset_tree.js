frappe.treeview_settings["Asset"] = {
	ignore_fields: ["parent_asset"],
	get_tree_nodes: 'erpnext.assets.doctype.asset.asset.get_children',
	add_tree_node: 'erpnext.assets.doctype.asset.asset.add_node',
	filters: [
		{
			fieldname: "asset",
			fieldtype: "Link",
			options: "Asset",
			label: __("Asset"),
			get_query: function () {
				return {
					filters: [["Asset", "is_group", "=", 1]]
				};
			}
		},
	],
	breadcrumb: "Assets",
	root_label: "All Assets",
	get_tree_root: false,
	menu_items: [
		{
			label: __("New Asset"),
			action: function () {
				frappe.new_doc("Asset", true);
			},
			condition: 'frappe.boot.user.can_create.indexOf("Asset") !== -1'
		}
	],
	onload: function (treeview) {
		treeview.make_tree();
	},
	disable_quick_entry: 1
};
