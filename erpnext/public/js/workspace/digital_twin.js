console.log("From custom Unity")

class UnityViewer{
    constructor(page){
        this.page = page;
        // temporary use first spacer wrapper
        this.main = page.wrapper.find(".spacer");
        this.setup_element();
    }

    setup_element(){
        this.wrapper = $("<div id='wrapper-custom'></div>");
        this.main.attr('style', 'height: max-content !important');
        this.main.append(this.wrapper);
        console.log(this.wrapper);
        this.render_unity();
    }

    render_unity(){
        var unity = `<iframe id="unity-view" src="/unity" title="W3Schools Free Online Web Tutorials"></iframe>`
        this.wrapper.append(unity)
    }
}


frappe.custom_workspace = (page)=>{
    setTimeout(()=>{
        new UnityViewer(page);
    }, 1000);
}