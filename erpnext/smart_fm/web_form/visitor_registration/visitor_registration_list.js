

frappe.custom_formatter_for_list = (fieldname, cell, value, doc)=>{

    if (fieldname=='status'){
        cell.addClass("status-cell");
        return change_status_field(cell, value);
    }else if(fieldname=='check_in_time'){
        
        cell.addClass("checkin checkin-cell");
        if (!value && ["Sign In", "Sign Out", "Accepted"].includes(doc.status) ){
            add_button(cell, "Check In", "btn-success", doc.name, "IN");
        }
        return cell
    }else if(fieldname=='check_out_time'){
        
        cell.addClass("checkout checkin-cell");
        if (!value && ["Sign In", "Sign Out", "Accepted"].includes(doc.status)){
            if (cint(doc.check_in)){
                add_button(cell, "Check Out", "btn-danger", doc.name, "OUT");
            }

        }
        return cell
    }else{
        return cell
    }
}

function add_button(cell, btn_name, btn_class, name, types){
    var btn = $(`<div class="btn-wrapper"><a class="btn ${btn_class} btn-sm" >${btn_name}</a></div>`);
    btn.on("click", ()=>{
        update_checkin_direct(cell, name, types);
    });
    cell.find("p").text("");
    cell.append(btn);
}

function change_status_field(cell, status){
    var place = $(cell).find('p');
    place.text(status).removeClass();
    place.addClass("indicator");
    place.addClass("indicator-pill");
    if (status=="Draft"){
        place.addClass("gray");
    }else if (status=="Sign In"){
        place.addClass("green");
    }else if (status=="Sign Out"){
        place.addClass("red");
    }else{
        place.addClass("blue");
    }
    return cell;
}

function update_checkin_direct(cell, name, types){
    // call and edit
    frappe.call({
        method:"erpnext.smart_fm.doctype.visitor_registration.visitor_registration.update_checkin",
        args:{
            name:name,
            types:types
        },
        btn:cell.find(".btn"),
        callback:(r)=>{

            // update cell
            cell.find(".btn-wrapper").remove();
            cell.find("p").text(r.message.time);
            // change status
            var parent = cell.parent();
            var status_cell = parent.find(".status-cell");
            change_status_field(status_cell, r.message.status);
            // active other button
            if (r.message.enable_in){
                var cur_cell = parent.find(".checkin");
                add_button(cur_cell, "Check In", "btn-success", name, "IN");
            }
            if (r.message.enable_out){
                var cur_cell = parent.find(".checkout");
                add_button(cur_cell, "Check Out", "btn-danger", name, "OUT");
            }
        }
    })

}