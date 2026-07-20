(function () {
	"use strict";

	var SCAN_DEBOUNCE_MS = 2000;
	var SCAN_FORMATS = ["qr_code", "ean_13", "ean_8", "code_128"];

	function escape_html(value) {
		return frappe.utils.escape_html(String(value == null ? "" : value));
	}

	function ensure_styles() {
		if (document.getElementById("warehouse-action-styles")) return;

		var style = document.createElement("style");
		style.id = "warehouse-action-styles";
		style.textContent = `
			.warehouse-action-picker { padding: 2px 0 8px; }
			.warehouse-action-picker__warehouse {
				display: flex; align-items: center; justify-content: space-between; gap: 12px;
				padding: 10px 12px; margin-bottom: 14px; border: 1px solid var(--border-color, #d1d8dd);
				border-radius: 8px; background: var(--control-bg, #f8f9fa);
			}
			.warehouse-action-picker__warehouse-label {
				font-size: 11px; color: var(--text-muted, #74808a); text-transform: uppercase; letter-spacing: .04em;
			}
			.warehouse-action-picker__warehouse-value { font-weight: 600; margin-top: 2px; }
			.warehouse-action-picker__hint { font-size: 12px; color: var(--text-muted, #74808a); margin: 0 0 12px; }
			.warehouse-action-cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
			.warehouse-action-card {
				appearance: none; width: 100%; min-height: 142px; padding: 16px 14px; text-align: left;
				border: 1px solid var(--border-color, #d1d8dd); border-radius: 10px;
				background: var(--card-bg, #fff); color: var(--text-color, #36414c); cursor: pointer;
				transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
			}
			.warehouse-action-card:hover, .warehouse-action-card:focus {
				border-color: var(--primary, #2490ef); box-shadow: 0 4px 14px rgba(36, 144, 239, .14);
				outline: none; transform: translateY(-1px);
			}
			.warehouse-action-card__icon {
				display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px;
				margin-bottom: 12px; border-radius: 8px; background: #eaf3ff; color: #1671c8;
				font-size: 17px; font-weight: 700;
			}
			.warehouse-action-card[data-action="Move"] .warehouse-action-card__icon { background: #fff5df; color: #a56b00; }
			.warehouse-action-card[data-action="Discard"] .warehouse-action-card__icon { background: #fff0f0; color: #c0392b; }
			.warehouse-action-card__title { display: block; font-weight: 650; font-size: 14px; margin-bottom: 5px; }
			.warehouse-action-card__description { display: block; font-size: 12px; line-height: 1.45; color: var(--text-muted, #74808a); }
			.warehouse-action-dialog .modal-dialog { max-width: 720px; }
			.warehouse-action-dialog .modal-body { padding: 18px 22px 12px; }
			.warehouse-action-dialog .form-group { margin-bottom: 14px; }
			.warehouse-action-intro {
				padding: 12px 14px; margin: 0 0 16px; border: 1px solid #dce9f7;
				border-radius: 8px; background: #f5f9fe;
			}
			.warehouse-action-intro__title { font-size: 14px; font-weight: 650; color: #205b91; }
			.warehouse-action-intro__details { font-size: 12px; color: var(--text-muted, #74808a); margin-top: 4px; }
			.warehouse-action-scan-button { margin-top: 24px; white-space: nowrap; }
			.warehouse-action-scanner { padding: 2px 0 4px; }
			.warehouse-action-scanner__video-wrap {
				position: relative; height: clamp(210px, 42vh, 330px); overflow: hidden;
				border-radius: 10px; background: #18252c;
			}
			.warehouse-action-scanner__video, .warehouse-action-scanner__preview {
				width: 100%; height: 100%; object-fit: cover; display: block;
			}
			.warehouse-action-scanner__preview { display: none; }
			.warehouse-action-scanner__video-overlay {
				position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; pointer-events: none;
			}
			.warehouse-action-scanner__frame {
				position: relative; width: min(72%, 270px); height: 92px; border: 2px solid #4bd18e;
				border-radius: 8px; box-shadow: 0 0 0 999px rgba(0, 0, 0, .18);
			}
			.warehouse-action-scanner__frame::after {
				content: ""; position: absolute; left: 9px; right: 9px; top: 50%; border-top: 1px solid rgba(255, 255, 255, .8);
			}
			.warehouse-action-scanner__camera-help {
				margin-top: 8px; text-align: center; font-size: 12px;
				color: var(--text-muted, #74808a);
			}
			.warehouse-action-scanner__camera-status {
				display: flex; align-items: center; gap: 7px; margin-top: 9px;
				font-size: 12px; color: var(--text-muted, #74808a);
			}
			.warehouse-action-scanner__status-dot { width: 8px; height: 8px; border-radius: 50%; background: #aab4ba; }
			.warehouse-action-scanner__status-dot.is-active { background: #2490ef; }
			.warehouse-action-scanner__status-dot.is-paused { background: #e1a62b; }
			.warehouse-action-scanner__status-dot.is-error { background: #d9534f; }
			.warehouse-action-scanner__notice {
				min-height: 48px; padding: 10px 12px; margin-top: 14px;
				border: 1px solid var(--border-color, #d1d8dd); border-radius: 8px; font-size: 12px;
			}
			.warehouse-action-scanner__notice.is-success { border-color: #b8e5ca; background: #eaf8f1; color: #167345; }
			.warehouse-action-scanner__notice.is-pending { border-color: #c9dff4; background: #f2f8fe; color: #28618e; }
			.warehouse-action-scanner__notice.is-error { border-color: #f0b5b5; background: #fff1f1; color: #a94442; }
			.warehouse-action-scanner__notice-title { font-weight: 650; }
			.warehouse-action-scanner__notice-detail { margin-top: 3px; color: var(--text-muted, #68757e); }
			.warehouse-action-scanner__result-label { display: block; margin-top: 11px; font-size: 12px; color: var(--text-muted, #68757e); }
			.warehouse-action-scanner__result { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-weight: 600; font-size: 14px; min-height: 42px; }
			.warehouse-action-scanner__hint { margin-top: 4px; font-size: 10px; color: var(--text-muted, #8a949b); }
			@media (max-width: 600px) {
				.warehouse-action-cards { grid-template-columns: 1fr; }
				.warehouse-action-card { min-height: auto; }
				.warehouse-action-dialog .modal-body { padding: 14px 16px 8px; }
			}
		`;
		document.head.appendChild(style);
	}

	function add_warehouse_action_menu_item() {
		var menu = document.querySelector("#toolbar-user");
		if (!menu || menu.querySelector('[data-label="Warehouse Action"]')) return;

		var divider = document.createElement("div");
		divider.className = "dropdown-divider warehouse-action-menu-item";
		menu.appendChild(divider);

		var item = document.createElement("a");
		item.className = "dropdown-item warehouse-action-menu-item";
		item.dataset.label = "Warehouse Action";
		item.href = "#";
		item.textContent = __("Warehouse Action");
		item.addEventListener("click", function (event) {
			event.preventDefault();
			open_warehouse_action_picker();
		});
		menu.appendChild(item);
	}

	$(document).on("toolbar_setup", add_warehouse_action_menu_item);
	$(document).on("page-change", add_warehouse_action_menu_item);
	window.addEventListener("load", add_warehouse_action_menu_item);

	function open_warehouse_action_picker() {
		ensure_styles();
		frappe.call({
			method: "erpnext.stock.doctype.warehouse_action.warehouse_action.get_action_context",
			callback: function (r) {
				if (r && r.message && r.message.warehouse) {
					show_picker_dialog(r.message);
				} else {
					frappe.msgprint({
						title: __("Warehouse Action"),
						message: __("Please configure Default Warehouse in Warehouse Location Settings first."),
						indicator: "orange",
					});
				}
			},
			error: function () {
				frappe.msgprint({
					title: __("Warehouse Action"),
					message: __("Could not load Warehouse Action settings."),
					indicator: "red",
				});
			},
		});
	}

	function show_picker_dialog(ctx) {
		var warehouse_label = ctx.warehouse_code ? ctx.warehouse + " (" + ctx.warehouse_code + ")" : ctx.warehouse;
		var html =
			'<div class="warehouse-action-picker">' +
				'<div class="warehouse-action-picker__warehouse"><div><div class="warehouse-action-picker__warehouse-label">' +
				__("Default Warehouse") + '</div><div class="warehouse-action-picker__warehouse-value">' +
				escape_html(warehouse_label) + '</div></div><span class="indicator-pill green">' + __("Ready") + '</span></div>' +
				'<p class="warehouse-action-picker__hint">' +
				__("Choose an operation to continue. Stock is updated only after the action is submitted.") + '</p>' +
				'<div class="warehouse-action-cards">' +
				action_card("New", "＋", __("New"), __("Assign batch to location.")) +
				action_card("Move", "↔", __("Move"), __("Relocate stock between locations.")) +
				action_card("Discard", "−", __("Discard"), __("Remove stock from a location.")) +
				'</div></div>';

		var d = new frappe.ui.Dialog({
			title: __("Warehouse Action"),
			indicator: "blue",
			fields: [{ fieldtype: "HTML", fieldname: "picker_html", options: html }],
			primary_action_label: null,
			hide_primary_action: true,
		});
		d.show();
		d.$wrapper.find(".warehouse-action-card").on("click", function () {
			var action_type = this.dataset.action;
			d.hide();
			open_warehouse_action_form(action_type, ctx);
		});
	}

	function action_card(action_type, icon, title, description) {
		return '<button type="button" class="warehouse-action-card" data-action="' + escape_html(action_type) +
			'" aria-label="' + escape_html(title) + '"><span class="warehouse-action-card__icon" aria-hidden="true">' +
			escape_html(icon) + '</span><span class="warehouse-action-card__title">' + escape_html(title) +
			'</span><span class="warehouse-action-card__description">' + escape_html(description) + '</span></button>';
	}

	function form_intro(action_type, ctx) {
		var descriptions = {
			New: __("Assign a batch to a warehouse location."),
			Move: __("Relocate a batch between warehouse locations."),
			Discard: __("Remove a batch quantity from a warehouse location."),
		};
		var warehouse_label = ctx.warehouse_code ? ctx.warehouse + " (" + ctx.warehouse_code + ")" : ctx.warehouse;
		return '<div class="warehouse-action-intro"><div class="warehouse-action-intro__title">' +
			escape_html(descriptions[action_type]) + '</div><div class="warehouse-action-intro__details">' +
			escape_html(__("Warehouse: {0}", [warehouse_label])) + '</div></div>';
	}

	function open_warehouse_action_form(action_type, ctx) {
		ensure_styles();
		var fields = [
			{ fieldname: "action_type", fieldtype: "Data", default: action_type, hidden: 1, read_only: 1 },
			{ fieldname: "action_intro", fieldtype: "HTML", options: form_intro(action_type, ctx) },
			{ fieldtype: "Section Break", label: __("Batch and Item") },
			{
				fieldname: "batch", fieldtype: "Link", label: __("Batch"), options: "Batch", reqd: 1,
				onchange: function () { set_batch_context(d, this.get_value()); },
			},
			{ fieldname: "item", fieldtype: "Link", label: __("Item"), options: "Item", read_only: 1 },
		];

		if (action_type === "Move" || action_type === "Discard") {
			fields.push(
				{ fieldtype: "Section Break", label: __("Source Location") },
				{
					fieldname: "from_location",
					fieldtype: "Link",
					label: __("From Location"),
					options: "Warehouse Location",
					reqd: 1,
					filters: location_filters(ctx),
					onchange: function () { set_available_stock_qty(d); },
				},
				{
					fieldname: "available_stock_qty",
					fieldtype: "Float",
					label: __("Available Stock Qty"),
					read_only: 1,
				},
				{
					fieldname: "available_stock_uom",
					fieldtype: "Link",
					label: __("Available Stock UOM"),
					options: "UOM",
					read_only: 1,
				}
			);
		}
		if (action_type === "New" || action_type === "Move") {
			fields.push(
				{ fieldtype: "Section Break", label: __("Target Location") },
				{ fieldname: "to_location", fieldtype: "Link", label: __("To Location"), options: "Warehouse Location", reqd: 1, filters: location_filters(ctx) }
			);
		}

		fields.push(
			{ fieldtype: "Section Break", label: __("Quantity") },
			{ fieldname: "qty", fieldtype: "Float", label: __("Quantity"), reqd: 1, onchange: function () { update_stock_qty(d); } },
			{
				fieldname: "uom", fieldtype: "Link", label: __("Transaction UOM"), options: "UOM", reqd: 1,
				onchange: function () { set_conversion_factor(d, d.get_value("item"), this.get_value()); },
			},
			{ fieldname: "conversion_factor", fieldtype: "Float", label: __("Conversion Factor"), reqd: 1, default: 1, read_only: 1 },
			{ fieldname: "stock_uom", fieldtype: "Link", label: __("Stock UOM"), options: "UOM", read_only: 1 },
			{ fieldname: "stock_qty", fieldtype: "Float", label: __("Stock Quantity"), read_only: 1 },
			{ fieldname: "remarks", fieldtype: "Small Text", label: __("Remarks") }
		);

		var d = new frappe.ui.Dialog({
			title: __("Warehouse Action") + " · " + __(action_type),
			indicator: action_type === "Discard" ? "orange" : "blue",
			fields: fields,
			primary_action_label: __("Submit Action"),
			primary_action: function () { submit_warehouse_action(d); },
			secondary_action_label: __("Cancel"),
			secondary_action: function () { d.hide(); },
		});
		d.show();
		d.$wrapper.addClass("warehouse-action-dialog");
		set_uom_query(d, []);
		attach_scan_button(d, "batch", "Batch");
		if (action_type === "Move" || action_type === "Discard") attach_scan_button(d, "from_location", "Warehouse Location");
		if (action_type === "New" || action_type === "Move") attach_scan_button(d, "to_location", "Warehouse Location");
		update_stock_qty(d);
	}

	function location_filters(ctx) {
		return { warehouse: ctx.warehouse, disabled: 0, status: ["!=", "Blocked"] };
	}

	function attach_scan_button(dialog, fieldname, expected_type) {
		var wrapper = dialog.$wrapper.find('[data-fieldname="' + fieldname + '"]');
		if (!wrapper.length || wrapper.find(".warehouse-action-scan-button").length) return;

		var button = $('<button type="button" class="btn btn-xs btn-default warehouse-action-scan-button"><i class="fa fa-camera"></i> ' +
			escape_html(__("Scan")) + '</button>');
		var link_button = wrapper.find(".link-btn");
		if (link_button.length) link_button.before(button);
		else wrapper.find(".control-input").append(button);
		button.on("click", function (event) {
			event.preventDefault();
			open_scan_dialog({
				expected_type: expected_type,
				on_submit: function (raw_code) {
					dialog.set_value(fieldname, raw_code);
					if (fieldname === "batch") set_batch_context(dialog, raw_code);
				},
			});
		});
	}

	function set_batch_context(dialog, batch) {
		if (!dialog) return;
		if (!batch) {
			dialog.set_value("item", "");
			dialog.set_value("stock_uom", "");
			dialog.set_value("uom", "");
			dialog.set_value("conversion_factor", 0);
			if (dialog.has_field("from_location")) {
				dialog._warehouse_action_source_locations = [];
				dialog.set_value("from_location", "");
				set_source_location_query(dialog, []);
				clear_available_stock(dialog);
			}
			set_uom_query(dialog, []);
			update_stock_qty(dialog);
			return;
		}

		if (dialog.has_field("from_location")) {
			dialog._warehouse_action_source_locations = [];
			dialog.set_value("from_location", "");
			set_source_location_query(dialog, []);
			clear_available_stock(dialog);
		}

		frappe.call({
			method: "frappe.client.get_value",
			args: { doctype: "Batch", filters: { name: batch }, fieldname: "item" },
			callback: function (batch_response) {
				if (!batch_response || !batch_response.message || dialog.get_value("batch") !== batch) return;
				var item = batch_response.message.item;
				dialog.set_value("item", item);
				load_item_uom_context(dialog, item, batch);
				load_batch_source_locations(dialog, batch);
			},
		});
	}

	function load_batch_source_locations(dialog, batch) {
		if (!dialog || !dialog.has_field("from_location")) return;

		if (!batch) {
			set_source_location_query(dialog, []);
			clear_available_stock(dialog);
			return;
		}

		frappe.call({
			method: "erpnext.stock.doctype.warehouse_action.warehouse_action.get_batch_source_locations",
			args: { batch: batch },
			callback: function (response) {
				if (dialog.get_value("batch") !== batch) return;
				var locations = (response && response.message) || [];
				dialog._warehouse_action_source_locations = locations;
				set_source_location_query(dialog, locations);

				var selected_location = dialog.get_value("from_location");
				if (!locations.some(function (row) { return row.warehouse_location === selected_location; })) {
					dialog.set_value("from_location", "");
					clear_available_stock(dialog);
				} else {
					set_available_stock_qty(dialog);
				}
			},
			error: function () {
				if (dialog.get_value("batch") !== batch) return;
				dialog._warehouse_action_source_locations = [];
				set_source_location_query(dialog, []);
				clear_available_stock(dialog);
			},
		});
	}

	function set_source_location_query(dialog, locations) {
		var location_field = dialog && dialog.get_field("from_location");
		if (!location_field) return;

		var names = locations.map(function (row) { return row.warehouse_location; }).filter(Boolean);
		var filters = names.length
			? { name: ["in", names] }
			: { name: ["in", ["__no_batch_location__"]] };
		var query = function () {
			return { filters: filters };
		};

		// Dialog Link controls read either the instance query or df query depending
		// on when the control was initialized. Keep both in sync.
		location_field.get_query = query;
		location_field.df.get_query = query;
		location_field.df.filters = filters;
		if (location_field.$input && location_field.$input.cache) {
			location_field.$input.cache[location_field.get_options()] = {};
		}
		if (location_field.awesomplete) {
			location_field.awesomplete.list = [];
		}
		location_field.refresh();
	}

	function clear_available_stock(dialog) {
		if (!dialog) return;
		dialog._warehouse_action_source_stock_qty = null;
		dialog._warehouse_action_source_stock_uom = "";
		if (dialog.has_field("available_stock_qty")) dialog.set_value("available_stock_qty", 0);
		if (dialog.has_field("available_stock_uom")) dialog.set_value("available_stock_uom", "");
		if (dialog.has_field("from_location")) update_stock_qty(dialog);
	}

	function set_available_stock_qty(dialog) {
		if (!dialog || !dialog.has_field("from_location")) return;
		var batch = dialog.get_value("batch");
		var selected_location = dialog.get_value("from_location");
		if (!batch || !selected_location) {
			clear_available_stock(dialog);
			return;
		}

		var locations = dialog._warehouse_action_source_locations || [];
		var source = locations.find(function (row) {
			return row.warehouse_location === selected_location;
		});
		if (source) {
			apply_available_stock(dialog, source);
			return;
		}

		// Fetch the selected row directly as a fallback for a Link value entered
		// before the source-location list request finished.
		frappe.call({
			method: "erpnext.stock.doctype.warehouse_action.warehouse_action.get_batch_location_stock",
			args: { batch: batch, warehouse_location: selected_location },
			callback: function (response) {
				if (dialog.get_value("batch") !== batch || dialog.get_value("from_location") !== selected_location) return;
				var stock = response && response.message;
				if (!stock || !flt(stock.qty)) {
					clear_available_stock(dialog);
					return;
				}
				apply_available_stock(dialog, {
					qty: stock.qty,
					stock_uom: stock.stock_uom,
					warehouse_location: selected_location,
				});
			},
			error: function () {
				if (dialog.get_value("batch") === batch && dialog.get_value("from_location") === selected_location) {
					clear_available_stock(dialog);
				}
			},
		});
	}

	function apply_available_stock(dialog, source) {
		var available_qty = flt(source.qty);
		dialog._warehouse_action_source_stock_qty = available_qty;
		dialog._warehouse_action_source_stock_uom = source.stock_uom || dialog.get_value("stock_uom");
		dialog.set_value("available_stock_qty", available_qty);
		dialog.set_value("available_stock_uom", dialog._warehouse_action_source_stock_uom);

		var conversion_factor = flt(dialog.get_value("conversion_factor"));
		if (!conversion_factor) {
			dialog.set_value("stock_qty", available_qty);
			return;
		}

		var set_qty = dialog.set_value("qty", available_qty / conversion_factor);
		if (set_qty && set_qty.then) {
			set_qty.then(function () {
				if (dialog._warehouse_action_source_stock_qty === available_qty) {
					dialog.set_value("stock_qty", available_qty);
				}
			});
		} else {
			dialog.set_value("stock_qty", available_qty);
		}
	}

	function sync_source_quantity_after_conversion(dialog) {
		var available_qty = flt(dialog && dialog._warehouse_action_source_stock_qty);
		var conversion_factor = flt(dialog && dialog.get_value("conversion_factor"));
		if (!dialog || !available_qty || !conversion_factor) return false;

		var set_qty = dialog.set_value("qty", available_qty / conversion_factor);
		if (set_qty && set_qty.then) {
			set_qty.then(function () {
				if (flt(dialog._warehouse_action_source_stock_qty) === available_qty) {
					dialog.set_value("stock_qty", available_qty);
				}
			});
		} else {
			dialog.set_value("stock_qty", available_qty);
		}
		return true;
	}

	function load_item_uom_context(dialog, item, batch) {
		frappe.call({
			method: "frappe.client.get",
			args: { doctype: "Item", name: item },
			callback: function (response) {
				if (!response || !response.message || dialog.get_value("batch") !== batch) return;

				var item_doc = response.message;
				var stock_uom = item_doc.stock_uom;
				var packaging_uoms = (item_doc.packaging || [])
					.map(function (row) { return row.uom; })
					.filter(Boolean);
				var allowed_uoms = unique_values(packaging_uoms.concat(stock_uom || ""));
				var current_uom = dialog.get_value("uom");
				var selected_uom = allowed_uoms.indexOf(current_uom) !== -1 ? current_uom : stock_uom;

				dialog.set_value("stock_uom", stock_uom || "");
				set_uom_query(dialog, allowed_uoms);
				dialog.set_value("uom", selected_uom || "");
				set_conversion_factor(dialog, item, selected_uom);
			},
		});
	}

	function unique_values(values) {
		return values.filter(function (value, index) {
			return value && values.indexOf(value) === index;
		});
	}

	function set_uom_query(dialog, allowed_uoms) {
		var uom_field = dialog && dialog.get_field("uom");
		if (!uom_field) return;

		var filters = allowed_uoms.length
			? { name: ["in", allowed_uoms] }
			: { name: ["in", ["__no_item_uom__"]] };
		uom_field.get_query = function () {
			return { filters: filters };
		};
		uom_field.refresh();
	}

	function set_conversion_factor(dialog, item, uom) {
		if (!dialog || !item || !uom) {
			dialog.set_value("conversion_factor", 0);
			update_stock_qty(dialog);
			return;
		}

		if (uom === dialog.get_value("stock_uom")) {
			dialog.set_value("conversion_factor", 1);
			if (!sync_source_quantity_after_conversion(dialog)) update_stock_qty(dialog);
			return;
		}

		var request_item = item;
		var request_uom = uom;
		frappe.call({
			method: "erpnext.stock.get_item_details.get_conversion_factor",
			args: { item_code: request_item, uom: request_uom },
			callback: function (response) {
				if (
					!response ||
					!response.message ||
					dialog.get_value("item") !== request_item ||
					dialog.get_value("uom") !== request_uom
				) return;
				dialog.set_value("conversion_factor", flt(response.message.conversion_factor || 0));
				if (!sync_source_quantity_after_conversion(dialog)) update_stock_qty(dialog);
			},
			error: function () {
				if (dialog.get_value("item") === request_item && dialog.get_value("uom") === request_uom) {
					dialog.set_value("conversion_factor", 0);
					update_stock_qty(dialog);
				}
			},
		});
	}

	function update_stock_qty(dialog) {
		if (!dialog) return;
		dialog.set_value("stock_qty", flt(dialog.get_value("qty") || 0) * flt(dialog.get_value("conversion_factor") || 0));
	}

	function submit_warehouse_action(dialog) {
		var values = dialog.get_values();
		if (!values) return;

		if ((values.action_type === "Move" || values.action_type === "Discard") && dialog.has_field("available_stock_qty")) {
			var available_stock_qty = flt(values.available_stock_qty || 0);
			var requested_stock_qty = flt(values.qty || 0) * flt(values.conversion_factor || 0);
			if (requested_stock_qty > available_stock_qty) {
				frappe.msgprint({
					title: __("Insufficient Location Stock"),
					message: __("Requested stock quantity ({0}) exceeds the available quantity ({1}) at this location.", [
						requested_stock_qty,
						available_stock_qty,
					]),
					indicator: "orange",
				});
				return;
			}
		}

		var button = dialog.get_primary_btn();
		button.prop("disabled", true).addClass("disabled");
		frappe.call({
			method: "frappe.client.insert",
			args: {
				doc: {
					doctype: "Warehouse Action", action_type: values.action_type, batch: values.batch,
					from_location: values.from_location || "", to_location: values.to_location || "",
					qty: values.qty, uom: values.uom, conversion_factor: values.conversion_factor,
					remarks: values.remarks || "",
				},
			},
			callback: function (r) {
				if (!r || !r.message || !r.message.name) {
					button.prop("disabled", false).removeClass("disabled");
					return;
				}
				frappe.call({
					method: "frappe.client.submit",
					args: { doc: r.message },
					callback: function () {
						frappe.show_alert({ message: __("Warehouse Action submitted successfully."), indicator: "green" });
						dialog.hide();
					},
					error: function (err) {
						button.prop("disabled", false).removeClass("disabled");
						frappe.msgprint({ title: __("Submit failed"), message: (err && err.message) || __("Could not submit Warehouse Action."), indicator: "red" });
					},
				});
			},
			error: function (err) {
				button.prop("disabled", false).removeClass("disabled");
				frappe.msgprint({ title: __("Could not save"), message: (err && err.message) || __("Could not create Warehouse Action."), indicator: "red" });
			},
		});
	}

	function open_scan_dialog(opts) {
		var expected_type = opts.expected_type;
		var stream = null;
		var detector = null;
		var detector_frame = null;
		var validation_timer = null;
		var result_generation = 0;
		var camera_active = false;
		var camera_captured = false;
		var submitted = false;
		var result_valid = false;
		var validated_code = "";

		var html =
			'<div class="warehouse-action-scanner">' +
				'<div class="warehouse-action-scanner__video-wrap">' +
					'<video class="warehouse-action-scanner__video" autoplay playsinline muted></video>' +
					'<img class="warehouse-action-scanner__preview" alt="" />' +
					'<div class="warehouse-action-scanner__video-overlay"><div class="warehouse-action-scanner__frame"></div></div>' +
				'</div>' +
				'<div class="warehouse-action-scanner__camera-help">' + escape_html(__("Align barcode inside frame")) + '</div>' +
				'<div class="warehouse-action-scanner__camera-status"><span class="warehouse-action-scanner__status-dot"></span>' +
					'<span class="warehouse-action-scanner__camera-status-text">' + escape_html(__("Starting camera…")) + '</span></div>' +
				'<div class="warehouse-action-scanner__notice" aria-live="polite"><div class="warehouse-action-scanner__notice-title">' +
					escape_html(__("Waiting for barcode")) + '</div><div class="warehouse-action-scanner__notice-detail">' +
					escape_html(__("You can also type or paste a code below.")) + '</div></div>' +
				'<label class="warehouse-action-scanner__result-label" for="warehouse-action-scan-result">' + escape_html(__("Result")) + '</label>' +
				'<input id="warehouse-action-scan-result" class="form-control warehouse-action-scanner__result" autocomplete="off" spellcheck="false" />' +
				'<div class="warehouse-action-scanner__hint">' + escape_html(__("Raw code · validation starts 2 seconds after the last change")) + '</div>' +
			'</div>';

		var d = new frappe.ui.Dialog({
			title: __("Scan {0}", [expected_type]), indicator: "blue",
			fields: [{ fieldtype: "HTML", fieldname: "scan_html", options: html }],
			primary_action_label: __("Submit"), primary_action: submit_result,
			secondary_action_label: __("Restart"), secondary_action: restart,
		});
		d.show();
		d.$wrapper.addClass("warehouse-action-dialog");
		var wrapper = d.$wrapper[0];
		var video = wrapper.querySelector(".warehouse-action-scanner__video");
		var preview = wrapper.querySelector(".warehouse-action-scanner__preview");
		var result_input = wrapper.querySelector(".warehouse-action-scanner__result");
		var status_text = wrapper.querySelector(".warehouse-action-scanner__camera-status-text");
		var status_dot = wrapper.querySelector(".warehouse-action-scanner__status-dot");
		var notice = wrapper.querySelector(".warehouse-action-scanner__notice");
		var notice_title = wrapper.querySelector(".warehouse-action-scanner__notice-title");
		var notice_detail = wrapper.querySelector(".warehouse-action-scanner__notice-detail");
		var overlay = wrapper.querySelector(".warehouse-action-scanner__video-overlay");
		var submit_button = d.get_primary_btn();
		submit_button.prop("disabled", true);

		function set_camera_status(label, state) {
			status_text.textContent = label;
			status_dot.className = "warehouse-action-scanner__status-dot";
			if (state) status_dot.classList.add("is-" + state);
		}

		function set_notice(title, detail, state) {
			notice.className = "warehouse-action-scanner__notice" + (state ? " is-" + state : "");
			notice_title.textContent = title || "";
			notice_detail.textContent = detail || "";
			notice_detail.style.display = detail ? "block" : "none";
		}

		function enable_submit(enabled) {
			submit_button.prop("disabled", !enabled || submitted);
		}

		function invalidate_validation() {
			result_generation += 1;
			result_valid = false;
			validated_code = "";
			enable_submit(false);
			if (validation_timer) {
				clearTimeout(validation_timer);
				validation_timer = null;
			}
		}

		function schedule_validation(code) {
			invalidate_validation();
			code = (code || "").trim();
			if (!code) {
				set_notice(__("Waiting for barcode"), __("You can also type or paste a code below."));
				return;
			}
			var generation = result_generation;
			set_notice(__("Checking code…"), __("Validation starts after 2 seconds without changes."), "pending");
			validation_timer = setTimeout(function () {
				if (generation === result_generation) validate_code(code, generation);
			}, SCAN_DEBOUNCE_MS);
		}

		function set_result(code) {
			result_input.value = code || "";
			schedule_validation(code);
		}

		function validate_code(code, generation) {
			var fieldname = expected_type === "Batch"
				? JSON.stringify(["name", "item"])
				: JSON.stringify(["name", "warehouse", "status", "disabled"]);
			frappe.call({
				method: "frappe.client.get_value",
				args: { doctype: expected_type, filters: { name: code }, fieldname: fieldname },
				callback: function (r) {
					if (generation !== result_generation || result_input.value.trim() !== code) return;
					var message = r && r.message;
					if (!message || !message.name) {
						set_notice(__("{0} not found", [expected_type]), __("Check the label or scan again."), "error");
						return;
					}
					result_valid = true;
					validated_code = code;
					enable_submit(true);
					if (expected_type === "Batch") {
						set_notice(__("✓ Batch found"), message.item ? __("Item: {0}", [message.item]) : "", "success");
					} else {
						var detail = message.status || __("Location is available");
						if (message.warehouse) detail += " · " + __("Warehouse: {0}", [message.warehouse]);
						set_notice(__("✓ Location found"), detail, "success");
					}
				},
				error: function () {
					if (generation !== result_generation || result_input.value.trim() !== code) return;
					set_notice(__("Could not validate code"), __("Try again or enter a different code."), "error");
				},
			});
		}

		function create_detector() {
			if (!window.BarcodeDetector) return null;
			try {
				return new window.BarcodeDetector({ formats: SCAN_FORMATS });
			} catch (error) {
				try { return new window.BarcodeDetector(); } catch (fallback_error) { return null; }
			}
		}

		function scan_loop() {
			if (!camera_active || !detector || camera_captured) return;
			if (video.readyState >= 2) {
				detector.detect(video).then(function (codes) {
					if (!camera_active || camera_captured || !codes || !codes.length) return;
					var raw_value = codes[0].rawValue;
					if (raw_value) capture_code(raw_value);
				}).catch(function () {}).finally(function () {
					if (camera_active && !camera_captured) detector_frame = requestAnimationFrame(scan_loop);
				});
			} else {
				detector_frame = requestAnimationFrame(scan_loop);
			}
		}

		function capture_code(raw_value) {
			if (!camera_active || camera_captured) return;
			camera_captured = true;
			capture_preview();
			stop_camera();
			set_camera_status(__("Camera paused · Captured"), "paused");
			set_result(raw_value);
		}

		function capture_preview() {
			try {
				if (video.readyState < 2 || !video.videoWidth || !video.videoHeight) return;
				var canvas = document.createElement("canvas");
				canvas.width = video.videoWidth;
				canvas.height = video.videoHeight;
				canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
				preview.src = canvas.toDataURL("image/jpeg", 0.85);
				preview.style.display = "block";
				video.style.display = "none";
				overlay.style.display = "none";
			} catch (error) {
				// Keep the final video frame visible when canvas capture is unavailable.
			}
		}

		function stop_camera() {
			camera_active = false;
			if (detector_frame) {
				cancelAnimationFrame(detector_frame);
				detector_frame = null;
			}
			if (stream) {
				stream.getTracks().forEach(function (track) { track.stop(); });
				stream = null;
			}
			if (video) video.pause();
		}

		function start_camera() {
			stop_camera();
			camera_captured = false;
			preview.removeAttribute("src");
			preview.style.display = "none";
			video.style.display = "block";
			overlay.style.display = "flex";
			set_camera_status(__("Starting camera"));
			if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
				set_camera_status(__("Camera unavailable"), "error");
				set_notice(__("Camera unavailable"), __("Type or paste a code manually below."), "error");
				return;
			}
			navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false }).then(function (media_stream) {
				stream = media_stream;
				video.srcObject = media_stream;
				camera_active = true;
				set_camera_status(__("Camera active"), "active");
				set_notice(__("Waiting for barcode"), __("You can also type or paste a code below."));
				detector = create_detector();
				if (detector) detector_frame = requestAnimationFrame(scan_loop);
				else set_notice(__("Camera ready"), __("Automatic detection is unavailable. Type or paste a code below."), "pending");
			}).catch(function () {
				set_camera_status(__("Camera unavailable"), "error");
				set_notice(__("Camera access denied"), __("Type or paste a code manually below."), "error");
			});
		}

		function restart() {
			invalidate_validation();
			result_input.value = "";
			set_notice(__("Waiting for barcode"), __("You can also type or paste a code below."));
			start_camera();
			result_input.focus();
		}

		function submit_result() {
			if (!result_valid || !validated_code || submitted) return;
			submitted = true;
			enable_submit(false);
			stop_camera();
			try {
				opts.on_submit(validated_code);
				d.hide();
			} catch (error) {
				submitted = false;
				enable_submit(true);
				frappe.msgprint({ title: __("Could not apply scan"), message: error.message || __("Could not update the target field."), indicator: "red" });
			}
		}

		result_input.addEventListener("input", function () { set_result(result_input.value); });
		d.$wrapper.on("hidden.bs.modal", function () {
			invalidate_validation();
			stop_camera();
		});
		start_camera();
	}

	window.open_scan_dialog = open_scan_dialog;
})();
