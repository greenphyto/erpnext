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
    },
    get_existing_lead: function(frm) {
        if (!frm.doc.new_customer) {
            frm.set_value({
                party_name: null,
                manual_address_line: null, manual_city: null, manual_state: null,
                manual_country: null, manual_tlp: null, manual_mobile_no: null,
                manual_email: null, manual_fax: null
            });
            return;
        }

        frm.call("get_existing_lead_from_new_customer").then((r) => {
            const data = r.message || {};
            if (!data.lead_name) {
                return;
            }

            frm.set_value("quotation_to", "Lead");
            frm.set_value({
                party_name: data.lead_name || null,
                manual_address_line: data.manual_address_line || null,
                manual_city: data.manual_city || null,
                manual_state: data.manual_state || null,
                manual_country: data.manual_country || null,
                manual_tlp: data.manual_tlp || null,
                manual_mobile_no: data.manual_mobile_no || null,
                manual_email: data.manual_email || null,
                manual_fax: data.manual_fax || null
            });
        });
    }
});

// Override to skip hard mandatory throw during Quotation flow switches.
erpnext.utils.set_taxes_from_address = function (
    frm,
    triggered_from_field,
    billing_address_field,
    shipping_address_field
) {
    if (frm.updating_party_details) return;

    const party = frm.doc.customer || frm.doc.supplier || frm.doc.lead || frm.doc.party_name;
    const posting_or_transaction_date = frm.doc.posting_date || frm.doc.transaction_date;

    if (frm.doc.doctype === "Quotation" && (!party || !posting_or_transaction_date)) {
        return;
    }

    if (frappe.meta.get_docfield(frm.doc.doctype, "taxes")) {
        if (!erpnext.utils.validate_mandatory(frm, "Lead / Customer / Supplier", party, triggered_from_field)) {
            return;
        }

        if (
            !erpnext.utils.validate_mandatory(
                frm,
                "Posting / Transaction Date",
                posting_or_transaction_date,
                triggered_from_field
            )
        ) {
            return;
        }
    } else {
        return;
    }

    frappe.call({
        method: "erpnext.accounts.party.get_address_tax_category",
        args: {
            tax_category: frm.doc.tax_category,
            billing_address: frm.doc[billing_address_field],
            shipping_address: frm.doc[shipping_address_field],
        },
        callback: function (r) {
            if (!r.exc) {
                if (frm.doc.tax_category != r.message) {
                    frm.set_value("tax_category", r.message);
                } else {
                    erpnext.utils.set_taxes(frm, triggered_from_field);
                }
            }
        },
    });
};

// Only require party_name for existing customer; new-customer flow keeps it optional/hidden.
if (erpnext.selling && erpnext.selling.QuotationController) {
    erpnext.selling.QuotationController.prototype.toggle_reqd_lead_customer = function () {
        if (this.frm.doc.is_existing_customer) {
            this.frm.toggle_reqd("party_name", this.frm.doc.quotation_to);
        } else {
            this.frm.toggle_reqd("party_name", 0);
        }
        this.frm.set_query("customer_address", this.address_query);
        this.frm.set_query("shipping_address_name", this.address_query);
    };

    erpnext.selling.QuotationController.prototype.customer_address = function () {
        if (
            this.frm.doc.quotation_to !== "Customer" ||
            !this.frm.doc.party_name ||
            !this.frm.doc.customer_address
        ) {
            return;
        }
        erpnext.utils.get_address_display(this.frm, "customer_address");
        erpnext.utils.set_taxes_from_address(
            this.frm,
            "customer_address",
            "customer_address",
            "shipping_address_name"
        );
    };
}
