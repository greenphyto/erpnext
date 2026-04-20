frappe.listview_settings['Payment Approval'] = {
    onload(listview) {
        // Tambah item di grup View (sejajar dengan Report, Dashboard, Kanban)
        const label = __('Bulk Approval');
        const action = () => frappe.set_route('payment-bulk-approval');
        // Beberapa versi Frappe tidak punya add_view_to_menu; gunakan add_button ke grup 'View'
        listview.page.add_button(label, action, __('View'));
    }
};
