
frappe.pages['batch-foms-details'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Batch FOMS Details'),
		single_column: true
	});
	page.start = 0;

	// page.warehouse_field = page.add_field({
	// 	fieldname: 'batch_no',
	// 	label: __('Batch No'),
	// 	fieldtype:'Data',
	// 	change: function() {
	// 		page.item_dashboard.start = 0;
	// 		page.item_dashboard.refresh();
	// 	}
	// });

	page.warehouse_field = page.add_field({
		fieldname: 'refresh',
		label: __('Refresh'),
		fieldtype:'Button',
		click: function() {
			page.item_dashboard.refresh();
		}
	});

	page.warehouse_field = page.add_field({
		fieldname: 'fetch_data',
		label: __('Fetch Data'),
		fieldtype:'Button',
		click: function() {
			page.item_dashboard.refresh(1);
		}
	});

	page.warehouse_field = page.add_field({
		fieldname: 'last_update',
		label: __('Last Fetch'),
		fieldtype:'Data',
		read_only:1,
	});

	page.warehouse_field = page.add_field({
		fieldname: 'hide_expired',
		label: __('Hide Expired'),
		fieldtype:'Check',
		read_only:0,
		change:function(){
			var value = this.get_value();
			var old_value = this.last_value;
			if (value!=old_value){
				console.log(this, value, old_value);
				page.item_dashboard.filters.hide_expired = value;
				page.item_dashboard.refresh(1);
			}
		}
	});

	page.warehouse_field = page.add_field({
		fieldname: 'hide_empty',
		label: __('Hide Empty'),
		fieldtype:'Check',
		read_only:0,
		change:function(){
			var value = this.get_value();
			var old_value = this.last_value;
			if (value!=old_value){
				console.log(this, value, old_value);
				page.item_dashboard.filters.hide_empty = value;
				page.item_dashboard.refresh(0);
			}
		}
	});

	page.warehouse_field = page.add_field({
		fieldname: 'sr_wrapper',
		label: __(''),
		fieldtype:'HTML',
		read_only:1,
	});

	page.warehouse_field = page.add_field({
		fieldname: 'batch_no',
		label: __('Search batch'),
		fieldtype:'Data',
		change:function(){
			var value = this.get_value();
			var old_value = this.last_value;
			if (value!=old_value){
				console.log(this, value, old_value);
				page.item_dashboard.filters.batch_no = value;
				page.item_dashboard.refresh(0);
			}
		}
	});

	frappe.require('item-dashboard.bundle.js', function() {
		page.item_dashboard = new erpnext.stock.BatchFOMS({
			page: page,
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
		this.stock_recon = "";
		this.filters = {};
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
	refresh(update=0) {
		if(this.before_refresh) {
			this.before_refresh();
		}

		var me = this;

		frappe.call({
			method: this.method,
			args: {
				update:update,
				filters:this.filters
			},
			callback: function (r) {
				r = r.message;
				console.log("Result", r)
				me.render(r);
				frappe.show_alert({
					message:"Refresh complete",
					indicator: "green"
				})
				me.hide_result(0);
			}
		});
		frappe.show_alert(({
			message:"Fetching in progress",
			indicator: "orange"
		}));
		me.hide_result(1);

	}
	render(res) {
		var me = this;
		var data = res.data;
		this.page.fields_dict.last_update.set_value(`On: ${res.last_fetch}`);

		this.update_stock_recon(res.stock_recon);

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
			var res = $(frappe.render_template(this.template, context))
			res.click(".btn-update-foms", function(el){
				var qty=0, batch_no;
				batch_no = $(el.target).attr("batch-no");
				qty = $(el.target).attr("qty");
				var type_batch = $(el.target).attr("btn-type");
				if (type_batch=='foms'){
					console.log(20, this, el);
					me.update_batch(batch_no, qty);
				}
			});
			res.appendTo(this.result);
		} else {
			var message = __("No Stock Available Currently");
			this.content.find('.result').css('text-align', 'center');

			$(`<div class='text-muted' style='margin: 20px 5px;'>
				${message} </div>`).appendTo(this.result);
		}
	}

	update_batch(batch_no, qty){
		frappe.call({
			method:"erpnext.stock.page.batch_foms_details.update_foms_batch",
			args:{
				batch_no:batch_no,
				qty:qty,
			},
			callback: (res)=>{
				console.log(208, res);
			}
		})
	}

	hide_result(hide=true){
		var loading_area = this.content.find(".loading-area");
		var result_area = this.content.find(".result-area");
		if (!hide){
			result_area.show();
			loading_area.hide();
		}else{
			result_area.hide();
			loading_area.show();
		}
	}

	update_stock_recon(stock_recon){
		var wrapper = $(this.page.parent).find('div[data-fieldname="sr_wrapper"]');
		wrapper.empty().append(`<div class="draft-recon">Draft Stock Recon: <br><a href="/app/stock-reconciliation/${stock_recon}">${stock_recon}</a></div>`)
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