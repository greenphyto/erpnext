<p>Dear Team,</p>
<p>The following items under <strong>Item Group: Products</strong> do not have a <strong>General Selling Price</strong> configured for one or more of their UOMs. Please review and update the Item Price accordingly.</p>

{% if doc.get_missing_item_price() %}
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 13px;">
    <thead style="background-color: #f0f0f0;">
        <tr>
            <th>Item Code</th>
            <th>Item Name</th>
            <th>Item Group</th>
            <th>Packing Size</th>
            <th>Rate</th>
        </tr>
    </thead>
    <tbody>
        {% for row in doc.get_missing_item_price() %}
        <tr>
            <td>{{ row.item_code }}</td>
            <td>{{ row.item_name }}</td>
            <td>{{ row.item_group }}</td>
            <td>{{ row.uom }}</td>
            <td>{{ row.rate }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
<p>Total missing: <strong>{{ doc.get_missing_item_price() | length }}</strong> item-UOM combination(s).</p>
{% else %}
<p style="color: green;">✅ All items have complete General Selling Prices for all UOMs.</p>
{% endif %}

<p>Please update the missing prices in <strong>ERPNext → Stock → Item Price</strong>.</p>
<p>Regards,<br>
<strong>ERPNext Automated Notification</strong></p>