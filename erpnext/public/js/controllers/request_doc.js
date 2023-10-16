
frappe.provide("cur_frm.cscript");
$.extend(cur_frm.cscript, {
  before_save: function(frm){
    return new Promise((resolve, reject) => {
      frappe.confirm(
        'Are you sure to save document?',
        function(){
          frappe.validated=true;
          resolve();
        },
        function(){
          frappe.validated=false;
          reject();
        }
      )
    })
  },
  refresh: function(){
    var frm = this.frm;
    if (frm.is_new() && frm.is_dirty()){
        frappe.db.get_value("User", frappe.session.user, [
            "email as email_address", 
            "full_name as name1", 
            "phone as phone_number"
        ]).then(r=>{
            frm.set_value(r.message);
        })
    }
  }
})