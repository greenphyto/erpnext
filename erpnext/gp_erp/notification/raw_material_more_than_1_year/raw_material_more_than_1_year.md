<p>Dear Team,</p>
<br>
<p>The following <strong>Raw Material</strong> batches have been in stock for more than <strong>1 year</strong>. Please review and take necessary action (usage, disposal, or scrap request).</p>
<br>
<table style="width: 100%; border-collapse: collapse;" border="1">
    <thead>
        <tr>
            <th style="padding: 6px;">Batch ID</th>
            <th style="padding: 6px;">Item</th>
            <th style="padding: 6px;">Manufacturing Date</th>
            <th style="padding: 6px;">Batch Qty</th>
            <th style="padding: 6px;">Link</th>
        </tr>
    </thead>
    <tbody>
        {% for b in doc.doc_list %}
        <tr>
            <td style="padding: 6px;">{{ b.name }}</td>
            <td style="padding: 6px;">{{ b.item }} - {{ b.item_name }}</td>
            <td style="padding: 6px;">{{ frappe.utils.formatdate(b.manufacturing_date) }}</td>
            <td style="padding: 6px;">{{ b.batch_qty }} {{ b.stock_uom }}</td>
            <td style="padding: 6px;">
                <a href="{{ frappe.utils.get_url('/app/batch/' + b.name) }}" target="_blank">View</a>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
<br>
<p>Total: <strong>{{ doc.doc_list | length }}</strong> batch(es).</p>
<br>
<p>Thank you.</p>
