
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
  }
})