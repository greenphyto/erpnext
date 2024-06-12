

frappe.custom_formatter_for_list = (fieldname, cell, value, doc)=>{

    if (fieldname=='workflow_state'){
        cell.addClass("status-cell");
        return change_status_field(cell, value);
    }else{
        return cell;
    }
}

function change_status_field(cell, status){
    var place = $(cell).find('p');
    place.text(status).removeClass();
    place.addClass("indicator");
    place.addClass("indicator-pill");
    if (status=="Draft"){
        place.addClass("gray");
    }else if (status=="Rejected"){
        place.addClass("red");
    }else if (status=="Submitted"){
        place.addClass("blue");
    }else if (status=="Rejected"){
        place.addClass("red");
    }else if (status=="Approved"){
        place.addClass("green");
    }else if (status=="Returned"){
        place.addClass("blue");
    }else if (status=="Issued"){
        place.addClass("purple");
    }else{
        place.addClass("gray");
    }
    return cell;
}