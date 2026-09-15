Found new zero rate for Stock Entry {{doc.name}}

{% set zero_rate_items = [] %}
{% for item in doc.items %}
    {% if item.basic_amount == 0 %}
        {% set _ = zero_rate_items.append(item) %}
    {% endif %}
{% endfor %}

{% if zero_rate_items %}
<table border="1" cellpadding="5" cellspacing="0">
    <thead>
        <tr>
            <th>Item Code</th>
            <th>Item Name</th>
            <th>Qty</th>
            <th>Rate</th>
            <th>Amount</th>
        </tr>
    </thead>
    <tbody>
        {% for item in zero_rate_items %}
        <tr>
            <td>{{ item.item_code }}</td>
            <td>{{ item.item_name }}</td>
            <td>{{ item.qty }}</td>
            <td>{{ item.basic_rate }}</td>
            <td>{{ item.basic_amount }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% else %}
<p>No zero rate items found.</p>
{% endif %}