
frappe.pages['batch-foms-details'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Batch FOMS Details'),
		single_column: true
	});
	page.start = 0;

	page.warehouse_field = page.add_field({
		fieldname: 'batch_no',
		label: __('Batch No'),
		fieldtype:'Data',
		change: function() {
			page.item_dashboard.start = 0;
			page.item_dashboard.refresh();
		}
	});

	page.warehouse_field = page.add_field({
		fieldname: 'fetch_data',
		label: __('Fetch Data'),
		fieldtype:'Button',
		description:"Last fetch on 12:23",
		change: function() {
			console.log("Fetch Data")
		}
	});

	page.warehouse_field = page.add_field({
		fieldname: 'last_update',
		label: __('Last Fetch'),
		fieldtype:'Datetime',
		read_only:1,
		default: "2024-10-10 13:21"
	});

	frappe.require('item-dashboard.bundle.js', function() {
		page.item_dashboard = new erpnext.stock.BatchFOMS({
			parent: page.main,
			page_length: 20,
			method: 'erpnext.stock.page.batch_foms_details.get_data',
			template: 'batch_foms_list'
		})

		page.item_dashboard.refresh();

		console.log("Page", page)
	});
}


frappe.provide('erpnext.stock');
erpnext.stock.BatchFOMS = class BatchFOMS {
	constructor(opts) {
		$.extend(this, opts);
		this.make();
	}
	make() {
		var me = this;
		this.start = 0;
		if (!this.sort_by) {
			this.sort_by = 'projected_qty';
			this.sort_order = 'asc';
		}

		this.content = $(frappe.render_template('batch_foms')).appendTo(this.parent);
		this.result = this.content.find('.result');

	}
	refresh() {
		if(this.before_refresh) {
			this.before_refresh();
		}

		var me = this;

		frappe.call({
			method: this.method,
			callback: function (r) {
				console.log("Result", r)
				me.render(r.message);
			}
		});
	}
	render(data) {
		if (this.start===0) {
			this.max_count = 0;
			this.result.empty();
		}

		let context = "";
		context = this.get_item_dashboard_data(data, this.max_count, true);
		
		this.max_count = this.max_count;

		// If not any stock in any warehouses provide a message to end user
		if (context.data.length > 0) {
			this.content.find('.result').css('text-align', 'unset');
			$(frappe.render_template(this.template, context)).appendTo(this.result);
		} else {
			var message = __("No Stock Available Currently");
			this.content.find('.result').css('text-align', 'center');

			$(`<div class='text-muted' style='margin: 20px 5px;'>
				${message} </div>`).appendTo(this.result);
		}
	}

	get_item_dashboard_data(data, max_count, show_item){
		return {
			data: data,
			max_count: 20,
			can_write: 1,
			show_item: false
		};
	}
}