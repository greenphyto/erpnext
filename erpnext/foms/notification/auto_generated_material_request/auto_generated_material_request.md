<p>Dear Team,</p>
<br>
<p>Please be informed that the following Material Request(s) have been automatically raised based on the item's re-order level:</p>
<br>
<div style="margin-bottom: 30px;">
	<p style="margin: 10px 0;">
		🔹 <strong>Material Request No.:</strong> 
		{{ frappe.utils.get_link_to_form("Material Request", doc.name) }}
	</p>

	<table style="width: 100%; border: 1px solid #d1d8dd; border-collapse: collapse;">
		<thead style="background-color: #f5f7fa;">
			<tr>
				<th style="border: 1px solid #d1d8dd; padding: 8px; text-align: left;">Item Code</th>
				<th style="border: 1px solid #d1d8dd; padding: 8px; text-align: left;">Warehouse</th>
				<th style="border: 1px solid #d1d8dd; padding: 8px; text-align: right;">Requested Qty</th>
				<th style="border: 1px solid #d1d8dd; padding: 8px; text-align: left;">UOM</th>
				<th style="border: 1px solid #d1d8dd; padding: 8px; text-align: right;">Current Projected Qty</th>
			</tr>
		</thead>
		<tbody>
			{% for item in doc.get("items") %}
			<tr>
				<td style="border: 1px solid #d1d8dd; padding: 8px;">
					<b>{{ item.item_code }}</b>
					{% if item.item_code != item.item_name %}
						({{ item.item_name }})
					{% endif %}
				</td>
				<td style="border: 1px solid #d1d8dd; padding: 8px;">{{ item.warehouse }}</td>
				<td style="border: 1px solid #d1d8dd; padding: 8px; text-align: right;">{{ item.qty }}</td>
				<td style="border: 1px solid #d1d8dd; padding: 8px;">{{ item.uom }}</td>
				<td style="border: 1px solid #d1d8dd; padding: 8px; text-align: right;">
					{{ frappe.utils.flt(item.projected_qty) + frappe.utils.flt(item.qty) }}
				</td>
			</tr>
			{% endfor %}
		</tbody>
	</table>

	<p style="margin-top: 10px;">
		This request ensures inventory continuity and was triggered as the projected stock approached the defined threshold.
	</p>
</div>
