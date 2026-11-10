<p>Dear Team,</p>
<br>
<p>The following <strong>Raw Material</strong> batches have not been reviewed for more than <strong>1 year</strong> (counted from the last audit date, or the manufacturing date if never audited) and have an inventory value of <strong>$100 or more</strong>. Please review and take necessary action (usage, disposal, or scrap request) after R&amp;D validation.</p>
<p><em>Batches with an inventory value below $100 have been written off automatically and are not listed here.</em></p>
<br>
<table style="width: 100%; border-collapse: collapse;" border="1">
    <thead>
        <tr>
            <th style="padding: 6px;">Batch ID</th>
            <th style="padding: 6px;">Item</th>
            <th style="padding: 6px;">Manufacturing Date</th>
            <th style="padding: 6px;">Last Audited</th>
            <th style="padding: 6px;">Batch Qty</th>
            <th style="padding: 6px;">Stock Value</th>
            <th style="padding: 6px;">Link</th>
        </tr>
    </thead>
    <tbody>
        {% for b in doc.doc_list %}
        <tr>
            <td style="padding: 6px;">{{ b.name }}</td>
            <td style="padding: 6px;">{{ b.item }} - {{ b.item_name }}</td>
            <td style="padding: 6px;">{{ frappe.utils.formatdate(b.manufacturing_date) }}</td>
            <td style="padding: 6px;">{{ frappe.utils.format_datetime(b.last_audited) if b.last_audited else "-" }}</td>
            <td style="padding: 6px;">{{ b.batch_qty }} {{ b.stock_uom }}</td>
            <td style="padding: 6px; text-align: right;">{{ frappe.utils.fmt_money(b.stock_value) }}</td>
            <td style="padding: 6px;">
                <a href="{{ frappe.utils.get_url('/app/batch/' + b.name) }}" target="_blank">View</a>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
<br>
<p>Total: <strong>{{ doc.doc_list | length }}</strong> batch(es) with a combined inventory value of <strong>{{ frappe.utils.fmt_money(doc.total_stock_value) }}</strong>.</p>
<p><em>Review these batches to assess potential write-offs.</em></p>
<br>
<p>Thank you.</p>
