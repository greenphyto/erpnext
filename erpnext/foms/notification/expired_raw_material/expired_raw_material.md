{% set today = frappe.utils.format_date(frappe.utils.add_days(frappe.utils.today(), -1)) %}
<H3>Raw Material is about expired</H3>

<p>Please note that the following raw materials in our inventory are approaching their expiration date within the next 30 days (as of <b>{{ today }}</b>):</p>

<table style="border-collapse: collapse; width: 100%;">
    <thead>
        <tr>
            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Product Name</th>
            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Batch Number</th>
            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Qty</th>
            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">UOM</th>
            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Expiry Date</th>
        </tr>
    </thead>
    <tbody>
        {% for d in doc.items %}
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px;">{{ d.item_code }}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{{ d.batch }}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{{ d.cur_qty }}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{{ d.uom }}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{{ d.expired_date }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<p>Scrap Request No: {{doc.name}}</p>
<a href="{{frappe.utils.get_url_to_form(doc.doctype, doc.name)}}">Open Document</a>

<p>Please review these materials and take necessary actions to ensure efficient usage before their expiry.</p>
<p>Thank you</p>
