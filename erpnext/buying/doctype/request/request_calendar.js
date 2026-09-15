// inject calendar card styles
if (!document.getElementById('request-calendar-styles')) {
	const style = document.createElement('style');
	style.id = 'request-calendar-styles';
	style.textContent = `
		.custom-calendar-container { padding: 0 15px; }
		.facility-cards { padding: 10px 0; }
		.facility-cards .left-tools { display: flex; gap: 8px; margin-bottom: 8px; }
		.facility-cards .left-tools a { cursor: pointer; color: var(--text-color); font-size: var(--text-sm); text-decoration: underline; }
		.card-scroll-row { display: flex; align-items: center; gap: 8px; }
		.card-search-box { position: relative; display: inline-flex; align-items: center; margin-left: 8px; }
		.card-search-input { padding: 3px 24px 3px 8px; border: 1px solid var(--border-color); border-radius: var(--border-radius-sm); font-size: var(--text-sm); width: 180px; outline: none; }
		.card-search-input:focus { border-color: var(--primary); }
		.card-search-clear { position: absolute; right: 6px; cursor: pointer; font-size: 14px; font-weight: 700; color: var(--text-muted); line-height: 1; display: none; }
		.card-search-input:not(:placeholder-shown) ~ .card-search-clear { display: block; }
		.card-list-wrapper { display: flex; overflow-x: auto; flex: 1; }
		.card-list-wrapper::-webkit-scrollbar { height: 4px; }
		.card-list-wrapper::-webkit-scrollbar-thumb { background: var(--gray-400); border-radius: 4px; }
		.card-list { display: flex; gap: 8px; flex-shrink: 0; }
		.facility-card { min-width: 220px; padding: 10px 14px; border: 1px solid var(--border-color); border-radius: var(--border-radius-md); cursor: pointer; background: var(--card-bg); flex-shrink: 0; }
		.facility-card:hover { box-shadow: var(--shadow-sm); }
		.facility-card .card-department { font-size: 10px; color: var(--text-muted); margin-bottom: 2px; }
		.facility-card .card-item-name { font-weight: 700; font-size: var(--text-md); margin-bottom: 4px; }
		.facility-card .card-req-count { font-size: var(--text-xs); color: var(--text-muted); }
		.facility-card .card-req-count .count { font-weight: 600; }
		.list-controller { display: flex; align-items: center; flex-shrink: 0; }
		.list-controller.hidden { display: none; }
		.list-controller .icon-btn { padding: 4px 8px; cursor: pointer; }
		.select-item-code { display: inline-flex; align-items: center; gap: 6px; background: var(--bg-green); color: #fff; padding: 2px 10px; border-radius: var(--border-radius-sm); font-size: var(--text-sm); margin-left: 10px; cursor: default; }
		.select-item-code .tag-close { cursor: pointer; font-weight: 700; font-size: 14px; line-height: 1; opacity: 0.7; }
		.select-item-code .tag-close:hover { opacity: 1; }
		.facilities-calendar-dialog .wrapper-list { display: flex; flex-wrap: wrap; gap: 8px; max-height: 400px; overflow-y: auto; }
	`;
	document.head.appendChild(style);
}

frappe.views.calendar["Request"] = {
	field_map: {
		start: "start",
		end: "end",
		id: "name",
		allDay: "allDay",
		title: "title",
		status: "status",
	},
	style_map: {
		Draft: "orange",
		Submit: "green",
	},
	options: {
		timeFormat: 'HH:mm',
		slotEventOverlap: false,
		slotDuration: '00:30:00',
		slotMinTime: "06:00:00",
		slotMaxTime: "20:00:00",
		axisFormat: 'HH:mm',
	},
	get_events_method: "erpnext.buying.doctype.request.request.get_events",
	hide_sidebar: true,
};

// Patch Calendar.prototype to support before_render and custom filters
if (!frappe.views.Calendar._make_patched) {
	const _original_make = frappe.views.Calendar.prototype.make;
	frappe.views.Calendar.prototype.make = function () {
		_original_make.call(this);
		if (this.before_render) {
			this.before_render(this);
		}
	};

	const _original_get_args = frappe.views.Calendar.prototype.get_args;
	frappe.views.Calendar.prototype.get_args = function (start, end) {
		var args = _original_get_args.call(this, start, end);
		if (this._custom_filters && this.doctype === "Request") {
			args.item_codes = JSON.stringify(this._custom_filters.item_codes || []);
		}
		return args;
	};

	// Patch prepare_colors to respect textColor from backend
	const _original_prepare_colors = frappe.views.Calendar.prototype.prepare_colors;
	frappe.views.Calendar.prototype.prepare_colors = function (d) {
		var custom_text_color = d.textColor;
		_original_prepare_colors.call(this, d);
		// restore textColor if backend provided a valid hex color
		if (custom_text_color && custom_text_color.startsWith("#")) {
			d.textColor = custom_text_color;
		}
		return d;
	};

	// Patch eventRender to show department as second line
	const _original_setup_options = frappe.views.Calendar.prototype.setup_options;
	frappe.views.Calendar.prototype.setup_options = function (defaults) {
		_original_setup_options.call(this, defaults);
		var original_eventRender = this.cal_options.eventRender;
		this.cal_options.eventRender = function (event, element) {
			if (original_eventRender) {
				original_eventRender(event, element);
			}
			if (event.tooltip && event.department) {
				var info_parts = [];
				if (event.department) info_parts.push(event.department);
				if (event.package_size) info_parts.push(event.package_size);
				element.find(".fc-title").html(
					`<div style="font-weight:600;">${event.title}</div>` +
					`<div style="font-size:0.8em;opacity:0.85;">${info_parts.join(' ')}</div>`
				);
			}
		};
	};

	frappe.views.Calendar._make_patched = true;
}

// Inject cards after calendar is ready
frappe.views.calendar["Request"].before_render = (calendar) => {
	calendar.custom = new RequestCards(calendar);
};

class RequestCards {
	constructor(calendar) {
		// this.main = the frappe.views.Calendar instance
		this.main = calendar;
		this.page = this.main.page;
		this.setup_container();
		this.get_main_data();
	}

	get_main_data() {
		var me = this;
		me.get_data().then(r => {
			me.data = r;
			me.setup_cards();
			me.setup_ui();
		});
	}

	setup_container() {
		this.container = $(`<div class="custom-calendar-container" id='request-calendar'></div>`);
		this.page.wrapper.find(".layout-main-section-wrapper").prepend(this.container);
		this.wrapper = $(`
		<div class="facility-cards">
			<div class="left-tools">
				<a class="show-all">Show All</a>
				<a class="clear-selected">clear</a>
				<div class="card-search-box">
					<input type="text" class="card-search-input" placeholder="Search item..." />
					<span class="card-search-clear">&times;</span>
				</div>
			</div>
			<div class="card-scroll-row">
				<div class="list-controller hidden">
					<div class="btn btn-default icon-btn left-arrow" style="display: none;">
						<svg class="icon icon-sm" style="">
							<use class="" href="#icon-left"></use>
						</svg>
					</div>
				</div>
				<div class="card-list-wrapper" id="scrollableElement">
					<div class="card-list" id="innerContent"></div>
				</div>
				<div class="list-controller hidden">
					<div class="btn btn-default icon-btn right-arrow">
						<svg class="icon icon-sm" style="">
							<use class="" href="#icon-right"></use>
						</svg>
					</div>
				</div>
			</div>
		</div>`);
		this.wrapper.appendTo(this.container);
		this.page.wrapper.find(".layout-main-section").appendTo(this.container);

		this.card_list = this.wrapper.find(".card-list");
		this.card_list_wrapper = this.wrapper.find(".card-list-wrapper");
	}

	setup_ui() {
		var me = this;
		var travel_size = 244;

		this.wrapper.find(".left-arrow").click(() => {
			me.card_list_wrapper.scrollLeft(me.card_list_wrapper.scrollLeft() - travel_size);
		});
		this.wrapper.find(".right-arrow").click(() => {
			me.card_list_wrapper.scrollLeft(me.card_list_wrapper.scrollLeft() + travel_size);
		});

		this.wrapper.find(".clear-selected").click(() => {
			me.filter_item_code("", true);
		});

		this.wrapper.find(".show-all").click(() => {
			me.show_all();
		});

		// card search: filter visible cards by item code or item name
		var search_input = this.wrapper.find(".card-search-input");
		search_input.on("input", function () {
			var term = $(this).val().toLowerCase();
			me.card_list.find(".facility-card").each(function () {
				var code = ($(this).data("item-code") || "").toLowerCase();
				var name = ($(this).data("item-name") || "").toLowerCase();
				$(this).toggle(code.indexOf(term) > -1 || name.indexOf(term) > -1);
			});
		});

		// clear search
		this.wrapper.find(".card-search-clear").click(function () {
			search_input.val("").trigger("input");
		});

		this.card_list_wrapper.on("scroll", () => {
			if (me.card_list_wrapper.scrollLeft() < 10) {
				me.wrapper.find(".left-arrow").hide();
			} else {
				me.wrapper.find(".left-arrow").show();
			}
		});

		// show arrows if needed
		setTimeout(() => {
			if (me.card_list_wrapper[0].scrollWidth > me.card_list_wrapper[0].clientWidth) {
				me.wrapper.find(".list-controller").removeClass("hidden");
			}
		}, 500);
	}

	get_card(data) {
		var me = this;
		var weight = data.total_weight ? `${data.total_weight} Kg` : '';
		var border_color = me.get_card_color(data.item_code);
		var card = $(`
			<div class="facility-card frappe-card" data-item-code="${data.item_code}" data-item-name="${data.item_name || ''}" style="border-left: 4px solid ${border_color};">
				<div class="card-department">${data.department || '-'}</div>
				<div class="card-item-name">${data.item_code} - ${weight}</div>
				<div class="card-req-count">Req count: <span class="count">${data.req_count || 0}</span></div>
			</div>
		`);

		card.on("click", function (e) {
			e.stopPropagation();
			var item_code = $(this).data("item-code");
			me.filter_item_code(item_code);
			if (me.all_dialog) {
				me.all_dialog.hide();
			}
		});

		return card;
	}

	get_card_color(item_code) {
		if (!item_code) return 'var(--border-color)';
		var prefix = item_code.toUpperCase();
		if (prefix.startsWith('PR-AV')) return '#FFC107';
		if (prefix.startsWith('PR-LV')) return '#28A745';
		if (prefix.startsWith('PR-HV')) return '#007BFF';
		return 'var(--border-color)';
	}

	get_text_color(item_code) {
		if (!item_code) return '#FFFFFF';
		var prefix = item_code.toUpperCase();
		if (prefix.startsWith('PR-AV')) return '#000000';
		return '#FFFFFF';
	}

	setup_cards() {
		var me = this;
		$.each(this.data, (i, d) => {
			var card = me.get_card(d);
			me.card_list.append(card);
		});
	}

	filter_item_code(item_code, remove = false) {
		var me = this;

		// initialize selected items array
		if (!me.main._custom_filters) {
			me.main._custom_filters = { item_codes: [] };
		}
		if (!me.main._custom_filters.item_codes) {
			me.main._custom_filters.item_codes = [];
		}

		if (remove && item_code) {
			// remove specific item code
			me.main._custom_filters.item_codes = me.main._custom_filters.item_codes.filter(c => c !== item_code);
		} else if (remove || !item_code) {
			// clear all
			me.main._custom_filters.item_codes = [];
		} else if (item_code) {
			// toggle: add if not exists, remove if exists
			var idx = me.main._custom_filters.item_codes.indexOf(item_code);
			if (idx > -1) {
				me.main._custom_filters.item_codes.splice(idx, 1);
			} else {
				me.main._custom_filters.item_codes.push(item_code);
			}
		}

		// update toolbar tags
		me.render_filter_tags();

		// refetch events
		me.main.$cal.fullCalendar('refetchEvents');
	}

	render_filter_tags() {
		var me = this;
		var cal_toolbar = me.main.$cal.find(".fc-toolbar .fc-left");
		cal_toolbar.find(".select-item-code").remove();

		var codes = me.main._custom_filters.item_codes || [];
		$.each(codes, (i, code) => {
			var tag_bg = me.get_card_color(code);
			var tag_fg = me.get_text_color(code);
			var tag = $(`<div class="select-item-code" style="background:${tag_bg};color:${tag_fg};">${code} <span class="tag-close" style="color:${tag_fg};">&times;</span></div>`);
			tag.find(".tag-close").on("click", function (e) {
				e.stopPropagation();
				me.filter_item_code(code, true);
			});
			cal_toolbar.append(tag);
		});

		if (codes.length > 0) {
			frappe.show_alert(__(`Filter: <b>${codes.join(", ")}</b>`), 2);
		} else {
			frappe.show_alert(__("Filter cleared"), 2);
		}
	}

	show_all() {
		var me = this;
		if (!me.all_dialog) {
			me.all_dialog = new frappe.ui.Dialog({
				title: 'Select Item',
				fields: [
					{
						label: 'Search',
						fieldname: 'item_code',
						fieldtype: 'Data',
						onchange: () => {
							me.update_dialog_list();
						}
					},
					{
						label: 'Items',
						fieldname: 'sec_break2',
						fieldtype: 'Section Break'
					},
					{
						label: '',
						fieldname: 'ht',
						fieldtype: 'HTML'
					}
				],
				size: 'large',
			});
		}

		me.all_dialog.show();

		var wrapper = this.all_dialog.fields_dict.ht.$wrapper;
		wrapper.empty().addClass("facilities-calendar-dialog");
		wrapper.append("<div class='wrapper-list'></div>");

		me.render_dialog_list({}, true);
	}

	update_dialog_list() {
		var load = false;
		var filters = {};

		var item_field = this.all_dialog.fields_dict.item_code;
		if (item_field.old_value != item_field.value) {
			item_field.old_value = item_field.value;
			load = true;
		}

		if (item_field.value) filters.item_code = item_field.value;

		if (load) {
			this.render_dialog_list(filters, true);
		}
	}

	render_dialog_list(filters = {}, clear = false) {
		var me = this;
		var temp = this.all_dialog.fields_dict.ht.$wrapper;
		var wrapper = temp.find(".wrapper-list");
		wrapper.hide();
		if (clear) {
			wrapper.empty();
		}
		this.get_data(filters).then(r => {
			var data = r;

			$.each(data, (i, d) => {
				var card = this.get_card(d);
				wrapper.append(card);
			});

			setTimeout(() => {
				wrapper.show();
			}, 100);
		});
	}

	get_data(filters) {
		return new Promise((resolve, reject) => {
			frappe.call({
				method: "erpnext.buying.doctype.request.request.get_request_items",
				args: {
					filters: filters
				},
				callback: r => {
					resolve(r.message || []);
				}
			});
		});
	}
}
