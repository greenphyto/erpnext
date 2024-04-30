frappe.listview_settings['Visitor Registration'] = {
	add_fields: ["docstatus", "status"],
	get_indicator: function(doc) {
        var status = {
            "Draft": [__("Draft"), "grey", "status,=,Draft"],
            "Sign In": [__("Sign In"), "green", "status,=,Sign In"],
            "Sign Out": [__("Sign Out"), "red", "status,=,Sign Out"],
            "Submitted": [__("Submitted"), "blue", "status,=,Submitted"],
        }
         return status[doc.status];
	},
    has_indicator_for_draft:1
};

frappe.help.youtube_id["BOM"] = "hDV0c1OeWLo";
