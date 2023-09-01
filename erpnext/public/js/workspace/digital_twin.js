console.log("Hello")

class UnityViewer{
    constructor(page){
        this.page = page;
        // temporary use first spacer wrapper
        this.main = page.wrapper.find(".spacer");
        this.setup_element();
    }

    setup_element(){
        this.wrapper = $("<div id='wrapper-custom'>OKEEE</div>");
        this.main.append(this.wrapper);
        console.log(this.wrapper);
        this.render_unity();
    }

    render_unity(){
        var unity = `<iframe src="/unity" title="W3Schools Free Online Web Tutorials"></iframe>`
        this.wrapper.append(unity)
    }
}


frappe.custom_workspace = (page)=>{
    console.log("19", page)
    new UnityViewer(page);
}