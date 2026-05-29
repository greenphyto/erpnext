frappe.listview_settings['Consignment Request'] = {
    add_fields: ["per_billed", "per_delivered", "per_sold", "per_return", "per_transfer"],

    get_indicator: function(doc) {
        let status = "Draft";
        let color = "gray";

        if (doc.per_billed > 0) {
            status = "Completed";
            color = "green";
        } else if (doc.per_delivered > 0) {
            status = "To Bill";
            color = "orange";
        } else if ((doc.per_sold > 0 || doc.per_return > 0) && doc.per_delivered == 0) {
            status = "Returned and To Bill";
            color = "red";
        } else if (doc.per_transfer == 100) {
            status = "Transfered and To Bill";
            color = "blue";
        } else if (doc.per_transfer > 0) {
            status = "Partially Transfered";
            color = "yellow";
        } else if (doc.per_transfer == 0) {
            status = "Waiting for Transfer";
            color = "gray";
        }

        return [__(status), color, "status,=," + status];
    }
};
