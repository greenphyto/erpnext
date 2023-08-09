// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Utility', {
	refresh: function(frm) {
    if (!frm.is_new()) {
			frm.add_custom_button(__("Meter Reading"), function() {
				frm.trigger("create_meter_reading");
			}, __("Create"));
    }

    set_meter_id(frm, 0);
	},

  create_meter_reading: function(frm) {
    frappe.call({
      args: {
        "name": frm.doc.name,
        "location": frm.doc.meter_location,
      },
      method: "erpnext.utilities.doctype.utility.utility.create_meter_reading",
      callback: function(r) {
        var doclist = frappe.model.sync(r.message);
        frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
      }
    });
  },

  type_of_meter: function(frm){
    set_meter_id(frm, 1);
  }
});

function set_meter_id(frm, force=0){
  if ((frm.doc.meter_id || !frm.is_dirty()) && !force ) return;
  // find last meter
  frappe.db.get_value("Utility", {
    "docstatus": 1, 
    "type_of_meter": frm.doc.type_of_meter, 
    "creation":['<', moment(frm.doc.creation)]
  }, "meter_id").then(r=>{
    if (r.message && r.message.meter_id){
      var meter_id = r.message.meter_id;
      function get_last_number(txt){
        txt = txt.replace(/[^0-9]/g, '|');
        var d = txt.split("|");
        var num = d[d.length-1];
        return num
      }

      var need_replace = get_last_number(meter_id)
      var new_id = cint(need_replace) + 1
      meter_id = meter_id.replace(need_replace, cstr(new_id))
      frm.set_value("meter_id", meter_id);
    }else{
      frm.set_value("meter_id", cstr(1) );
    }
  })

  console.log("here")
}