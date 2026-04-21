{% set today = frappe.utils.format_date(frappe.utils.add_days(frappe.utils.today(), -1)) %}

<H3>Product Waste ({{today}})</H3>

<p>Please note that the following products in our inventory have been disposed of as they have reached their expiration date as of <strong>{{ today }}</strong>:</p>

<table style="border-collapse: collapse; width: 100%;">
    <thead>
        <tr>
            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Product Name</th>
            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Batch Number</th>
            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Warehouse</th>
            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Qty</th>
            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">UOM</th>
        </tr>
    </thead>
    <tbody>
        {% for d in doc.items %}
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px;">{{ d.item_code }}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{{ d.batch_no }}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{{ d.s_warehouse }}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{{ d.qty }}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{{ d.uom }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<p>These items have been removed from our inventory as per our disposal policy for expired products.</p>
<p>Thank you</p>