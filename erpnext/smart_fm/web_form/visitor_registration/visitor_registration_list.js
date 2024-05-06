console.log("Here")

frappe.custom_formatter_for_list = (fieldname, value)=>{
    console.log(fieldname, value);
    if (fieldname!="status") return value;

    var place = $(value).find('p');
    var status = place.text();
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
    return value;
}