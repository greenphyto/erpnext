
frappe.pages['batch-foms-details'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('FOMS Batch Syncing'),
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
		this.warning = false;
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
			res.on("click", ".btn-add", function(el){
				var batch_no = $(el.target).attr("batch-no");
				var qty = $(el.target).attr("qty");
				var batch_id = $(el.target).attr("batch-id");
				var item_id = $(el.target).attr("item-id");
				var warehouseID = $(el.target).attr("warehouseID");
				var expired_date = $(el.target).attr("expired-date");
				var type_batch = $(el.target).attr("btn-type");
				if (type_batch=='foms'){
					me.show_update_progress(el, true);
					me.update_batch(batch_no,batch_id, warehouseID, qty).then(()=>{
						me.show_update_progress(el, false);
					});
				}else{
					me.show_update_progress(el, true);
					me.update_erp_batch(batch_no,batch_id, item_id, warehouseID, qty, expired_date).then(()=>{
						me.show_update_progress(el, false);
					});
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

	show_update_progress(el, start=false){
		if (start){
			$(el.currentTarget).addClass("row-onupdate");
		}else{
			$(el.currentTarget).removeClass("row-onupdate");
		}
	}

	update_batch(batch_no, batch_id, warehouseID, qty){
		var me = this;
		return new Promise((resolve)=>{
			frappe.call({
				method:"erpnext.stock.page.batch_foms_details.update_foms_batch",
				args:{
					batch_no:batch_no,
					batch_id:batch_id,
					qty:qty,
					warehouseID:warehouseID
				},
				callback: (res)=>{
					if (res.message){
						res = res.message;
						if (res.error){
							frappe.confirm(res.error,
								function(){ 
									frappe.set_route('query-report', "Batch-Wise Balance History", res.report_filter);
								},
								function(){ 
									
								}
							)

							console.log(res.error);
						}else{
							me.update_row(res, true);
						}
					}
					resolve()
				}
			})
		})
	}

	update_erp_batch(batch_no,batch_id, item_id, warehouseID, qty, expired_date){
		var me = this;
		return new Promise((resolve)=>{
			frappe.call({
				method:"erpnext.stock.page.batch_foms_details.update_erp_batch",
				args:{
					batch_no:batch_no,
					batch_id:batch_id,
					qty:qty,
					item_id: item_id,
					warehouseID:warehouseID,
					expired_date:expired_date
				},
				callback: (res)=>{
					if (res.message){
						if (res.message.error){
							frappe.msgprint(res.message.error);
						}else{
							me.update_row(res.message, false);
							if (res.message.stock_recon){
								me.update_stock_recon(res.message.stock_recon);
								if (!me.warning){
									frappe.msgprint("Please submit Stock Reconcilliation on the top corner after finish all update")
									me.warning=true;
								}
							}
						}
					}
					resolve()
				}
			})
		})
	}

	update_row(result, update_foms=true){

		frappe.show_alert(`Updated Batch ${result.batchRefNo}`,2)
		var row = $(`tr#batchID${result.id}`);
		row.find("button").attr("disabled", true);
		if (update_foms){
			row.find("td.foms-qty").text(result.qtyAdd);
			row.find("td.foms-exp").text( moment(result.expiryDate).format("DD-MM-yyyy") );
			row.find("button.btn-update-erp").attr("qty", result.qtyAdd)
		}else{
			row.find("td.erp-qty").text(result.qty);
			row.find("td.erp-exp").text(result.expired_date);
			row.find("button.btn-update-foms").attr("qty", result.qty)
		}
		row.fadeOut(100).fadeIn(100).fadeOut(100).fadeIn(100);
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
		if (stock_recon){
			wrapper.empty().append(`<div class="draft-recon">Draft Stock Recon: <br><a href="/app/stock-reconciliation/${stock_recon}">${stock_recon}</a></div>`)
		}else{
			wrapper.empty()
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