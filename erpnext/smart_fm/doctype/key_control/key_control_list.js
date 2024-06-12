frappe.listview_settings['Key Control'] = {
	add_fields: ["docstatus", "workflow_state"],
	get_indicator: function(doc) {
        var workflow_state = {
            "Draft": [__("Draft"), "grey", "workflow_state,=,Draft"],
            "Submitted": [__("Submitted"), "blue", "workflow_state,=,Submitted"],
            "Rejected": [__("Pending"), "red", "workflow_state,=,Rejected"],
            "Approved": [__("Approved"), "green", "workflow_state,=,Approved"],
            "Returned": [__("Returned"), "blue", "workflow_state,=,Returned"],
            "Issued": [__("Issued"), "purple", "workflow_state,=,Issued"],
        }
         return workflow_state[doc.workflow_state];
	},
    has_indicator_for_draft:1
};