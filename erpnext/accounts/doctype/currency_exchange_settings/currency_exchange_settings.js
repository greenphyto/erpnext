// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Currency Exchange Settings', {
	service_provider: function(frm) {
		if (frm.doc.service_provider == "exchangerate.host") {
			let result = ['result'];
			let params = {
				date: '{transaction_date}',
				from: '{from_currency}',
				to: '{to_currency}'
			};
			add_param(frm, "https://api.exchangerate.host/convert", params, result);
		} else if (frm.doc.service_provider == "frankfurter.app") {
			let result = ['rates', '{to_currency}'];
			let params = {
				base: '{from_currency}',
				symbols: '{to_currency}'
			};
			add_param(frm, "https://frankfurter.app/{transaction_date}", params, result);
		} else if (frm.doc.service_provider =="mas.gov.sg")
		{
			let result = ['elements','{from_currency}_{to_currency}'];
			let params = {
				end_of_day: '{transaction_date}',
			};
			let headers = {
				keyid: 'dd7a843f-d285-43bf-9adb-947e8ee87f48',
			};

			add_param(frm, "https://eservices.mas.gov.sg/apimg-gw/server/monthly_statistical_bulletin_non610ora/exchange_rates_end_of_period_daily/views/exchange_rates_end_of_period_daily?end_of_day={transaction_date}", params, result, headers);
		}

	}
});


function add_param(frm, api, params, result, headers={}) {
	var row;
	frm.clear_table("req_params");
	frm.clear_table("result_key");
	frm.clear_table("header_params");

	frm.doc.api_endpoint = api;

	$.each(params, function(key, value) {
		row = frm.add_child("req_params");
		row.key = key;
		row.value = value;
	});

	$.each(result, function(key, value) {
		row = frm.add_child("result_key");
		row.key = value;
	});

	$.each(result, function(key, value) {
		row = frm.add_child("header_params");
		row.key = value;
	});

	frm.refresh_fields();
}
