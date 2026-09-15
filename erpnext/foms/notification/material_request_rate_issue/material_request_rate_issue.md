<h3>Found Material Request rate with more than 100% increase</h3>
<br>
<p>Document Details:</p>
<p>Document No: <b>{{doc.name}}</b></p>
<p>Request Date: <b>{{doc.transaction_date}}</b></p>
<p>Project/Department: <b>{{doc.department}}</b></p>
<a href="{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}" class="btn"><h3>View Request</h3></a>
<br>
<table>
    <thead>
        <tr>
            <th>Item</th>
            <th>Cur Rate</th>
            <th>New Rate</th>
            <th>Increase</th>
        </tr>
    </thead>
    <tbody>
    {% for d in doc.get("issues") %}
        <tr>
            <td>{{d.item_code}}</td>
            <td>{{d.current_rate}}</td>
            <td>{{d.incoming_rate}}</td>
            <td class="warning">{{d.growth_rate}}%</td>
        </tr>
    {% endfor %}
    </tbody>
</table>
<br>
<p>This request requires your immediate attention before it can be converted to a Purchase Order.</p>
<br>