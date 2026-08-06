frappe.ui.form.on("Sales Order", {
    is_pledge: function(frm) {
        if (cint(frm.doc.is_pledge) == 0) {
            frm.set_value("customer", "");
            frm.set_value("naming_series", "SO.###./.YYYY");
            frm.set_value("po_no", "");
            frm.set_value("po_date", "");
            return;
        }
        frm.set_value("naming_series", 'PLN.###./.YYYY');
        frm.set_value("po_no", "For Pledge");
        frm.set_value("po_date", "");
        frappe.db.get_value("Company", frm.doc.company, "donor_customer").then(r => {
            if (r.message && r.message.donor_customer) {
                frm.set_value("customer", r.message.donor_customer);
            }
        });
    },

    pending_po: function(frm) {
        if (frm.doc.is_pledge) return;
        if (frm.doc.pending_po) {
            frm.set_value("po_no", "Pending PO");
            frm.set_value("po_date", "");
            frm.set_df_property("po_no", "hidden", 1);
            frm.set_df_property("po_date", "hidden", 1);
        } else {
            frm.set_value("po_no", "");
            frm.set_value("po_date", "");
            frm.set_df_property("po_no", "hidden", 0);
            frm.set_df_property("po_date", "hidden", 0);
        }
    },

    refresh: function(frm) {
        erpnext.selling.render_delivery_progress(frm);
    }
});

frappe.ui.form.on("Sales Order Item", {
    uom: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        frappe.db.get_value("Packaging", d.uom, "total_weight").then(r => {
            frappe.model.set_value(cdt, cdn, "weight_in_unit", r.message.total_weight);
        });
    }
});

erpnext.selling.render_delivery_progress = function(frm) {
    let total_qty = 0;
    let total_delivered = 0;

    (frm.doc.items || []).forEach(item => {
        total_qty += item.qty;
        total_delivered += item.delivered_qty;
    });

    let percentage = frm.doc.per_delivered || 0;

    let bar_class = 'bg-blue';
    if (percentage <= 30) bar_class = 'bg-red';
    else if (percentage === 100) bar_class = 'bg-green';

    let html_content = `
        <div class="progress-wrapper" style="margin-bottom: 10px; padding: 10px; border: 1px solid #f0f0f0; border-radius: 8px;">
            <div class="level" style="margin-bottom: 8px;">
                <div class="level-left">
                    <span class="text-muted" style="font-size: 13px;">
                        <strong>Delivered:</strong> ${total_delivered} / ${total_qty} Qty
                    </span>
                </div>
                <div class="level-right">
                    <span class="badge badge-pill ${percentage === 100 ? 'badge-success' : 'badge-info'}">
                        ${percentage.toFixed(0)}%
                    </span>
                </div>
            </div>
            <div class="progress-chart">
                <div class="progress" style="height: 12px; background-color: #ebf0f5; border-radius: 10px;">
                    <div class="progress-bar ${bar_class}"
                         role="progressbar"
                         style="width: ${percentage}%; border-radius: 10px; transition: width 0.5s ease;"
                         aria-valuenow="${percentage}"
                         aria-valuemin="0"
                         aria-valuemax="100">
                    </div>
                </div>
            </div>
        </div>
    `;

    frm.get_field('donor_info').$wrapper.html(html_content);
};
