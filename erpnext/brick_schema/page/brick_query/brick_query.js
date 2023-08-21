frappe.pages['brick-query'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Brick Query',
		single_column: true
	});

	frappe.require([
		"/assets/erpnext/js/lib/d3js.org_d3.v3.min.js",
		"/assets/erpnext/js/lib/d3sparql.js"
	], function(){
		frappe.brick = new BrickSchemaObject(wrapper)
	})
}

// STATUS: UNFINISHED
// Temporary use basic D3 Force Graph

class BrickSchemaObject{
	constructor(page){
		console.log("Libs", d3sparql);
		this.page = $(page);
		this.setup_wrapper();
	}
	
	setup_wrapper(){
		this.wrapper = this.page.find(".layout-main-section");
		this.setup_element();
	}

	setup_element(){
		this.elem = $( frappe.render_template('brick_query_page') );

		this.wrapper.append(this.elem);
	}
	exec() {
		/* Uncomment to see debug information in console */
		d3sparql.debug = true
		var endpoint = d3.select("#endpoint").property("value")
		var sparql = d3.select("#sparql").property("value")
		d3sparql.query(endpoint, sparql, this.render)
	}

	render(json) {
	  /* set options and call the d3spraql.xxxxx function in this library ... */
	  var config = {
        "charge": -500,
        "distance": 50,
        "width": 1000,
        "height": 750,
        "selector": "#result"
      }
      d3sparql.forcegraph(json, config)
	}
}

function exec(){
	frappe.brick.exec();
}