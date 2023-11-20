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

frappe.validate_email_field = function (fields){
    $.each(fields, (i,field)=>{
        frappe.web_form.on(field, (frm, value)=>{
            if (!frappe.utils.validate_type( value, 'email')){
                frappe.web_form.set_value(field, "")
            }
        })
    })
}

frappe.validate_phone_field_table = function(table_field, field){
    var grid = frappe.web_form.fields_dict[table_field].grid;
    grid.on(field, (t_field, idx, value)=>{ 
        if (!frappe.utils.validate_type( value, 'phone')){
           grid.grid_rows[idx-1].columns[field].field.set_value("");
        }
    })
}

frappe.validate_email_field_table = function(table_field, field){
    var grid = frappe.web_form.fields_dict[table_field].grid;
    grid.on(field, (t_field, idx, value)=>{ 
        if (!frappe.utils.validate_type( value, 'email')){
           grid.grid_rows[idx-1].columns[field].field.set_value("");
        }
    })
}