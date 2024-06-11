frappe.listview_settings['Permit to Work'] = {
	add_fields: ["docstatus", "workflow_state"],
	get_indicator: function(doc) {
        var workflow_state = {
            "Draft": [__("Draft"), "grey", "workflow_state,=,Draft"],
            "Sign In": [__("Sign In"), "green", "workflow_state,=,Sign In"],
            "Sign Out": [__("Sign Out"), "red", "workflow_state,=,Sign Out"],
            "Submitted": [__("Submitted"), "blue", "workflow_state,=,Submitted"],
            "Pending": [__("Pending"), "orange", "workflow_state,=,Pending"],
            "Approved": [__("Approved"), "blue", "workflow_state,=,Approved"],
        }
         return workflow_state[doc.workflow_state];
	},
    has_indicator_for_draft:1
};