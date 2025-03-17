frappe.listview_settings['Cleaning Checklist'] = {
	add_fields: ["posting_date", "cleaned_by", "status", "month", "year"],
	get_indicator: (doc) => {
		if (doc.docstatus==1) {
			return [__("Cleaned"), "green", "status,=,Cleaned"];
		} else if(doc.docstatus==0){
			return [__("Draft"), "gray", "docstatus,=,0"];
        } else{
			return [__("Cancelled"), "red", "docstatus,=,2"];
        }
	}
};
