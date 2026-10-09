frappe.ui.form.on('Quotation', {
    new_customer: function(frm) {
        frm.trigger("get_existing_lead");
    },
    is_existing_customer: function(frm) {
        if (!frm.doc.is_existing_customer) return;
        frm.set_value("quotation_to", "Customer");
        frm.set_value({
            party_name: null, new_customer: null,
            manual_address_line: null, manual_city: null, manual_state: null,
            manual_country: null, manual_contact_person_name: null,
            manual_tlp: null, manual_mobile_no: null, manual_email: null, manual_fax: null,
            customer_address: null, shipping_address_name: null,
            shipping_address: null, address_display: null,
            contact_person: null, contact_display: null,
            contact_mobile: null, contact_email: null, customer_name: null
        });
        frm.trigger("set_label");
        frm.trigger("toggle_reqd_lead_customer");
        frm.trigger("set_dynamic_field_label");
    }
});
