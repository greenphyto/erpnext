frappe.provide("frappe");
frappe.set_default_web_form = function (fields){
    if (frappe.web_form.is_new){
        frappe.call({
            method:"frappe.client.get_value",
            args:{
                doctype: "User",
                filters: {
                    "name": frappe.session.user
                },
                fieldname: fields,
                as_dict:1
            },
            callback: r=>{
                if(r.message){
                    r = r.message;
                    frappe.web_form.set_values(r);
                }
            }
        })
    }
}


frappe.validate_phone_field = function (fields){
    $.each(fields, (i,field)=>{
        frappe.web_form.on(field, (frm, value)=>{
            if (!frappe.utils.validate_type( value, 'phone')){
                frappe.web_form.set_value(field, "")
            }
        })
    })
}
