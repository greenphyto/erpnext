Rate anomaly detected in {{ doc.doctype }} <a href="{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}">{{ doc.name }}</a>:

<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
<tr><th>Item Code</th><th>Warehouse</th><th>Current Rate</th><th>Previous Rate</th><th>Diff %</th></tr>
{% for a in doc.anomalies %}
<tr>
<td>{{ a.item_code }}</td>
<td>{{ a.warehouse }}</td>
<td>{{ a.current_rate }}</td>
<td>{{ a.prev_rate }}</td>
<td>{{ a.diff_pct }}%</td>
</tr>
{% endfor %}
</table>