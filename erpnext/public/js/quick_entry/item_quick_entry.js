frappe.provide("frappe.quick_entry_controller")
frappe.quick_entry_controller['Item'] = {
    filters: {
        asset_code:()=>{
            return {
                query:"erpnext.assets.doctype.asset.asset.filter_account_for_asset_code",
            }
        }
    }
}