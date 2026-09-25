FOMS and ERP status mismatch found in Work Orders:
<table border="1" cellpadding="5" cellspacing="0">
	<tr>
		<th>Work Order</th>
		<th>FOMS Lot</th>
		<th>Operation</th>
		<th>FOMS Status</th>
		<th>ERP Status</th>
	</tr>

	{% for row in doc.get('foms_mismatches') %}
	<tr>
		<td>{{ row.work_order }}</td>
		<td>{{ row.lot }}</td>
		<td>{{ row.operation }}</td>
		<td>{{ row.foms_status }}</td>
		<td>{{ row.erp_status }}</td>
	</tr>
	{% endfor %}
</table>