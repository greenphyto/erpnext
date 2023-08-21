frappe.pages['brick-query'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Brick Query',
		single_column: true
	});
}