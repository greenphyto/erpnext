<p>Dear Manager,</p>
<br>
<p>Here is the list of <strong>Sales Invoices</strong> that are still in <strong>Draft</strong> status as of the end of {{ frappe.utils.formatdate(frappe.utils.nowdate(), "MMMM YYYY") }}. Please review and submit them if appropriate.</p>
<br>
<table style="width: 100%; border-collapse: collapse;" border="1">
    <thead>
        <tr>
            <th style="padding: 6px;">Invoice Name</th>
            <th style="padding: 6px;">Customer</th>
            <th style="padding: 6px;">Posting Date</th>
            <th style="padding: 6px;">Grand Total</th>
            <th style="padding: 6px;">Link</th>
        </tr>
    </thead>
    <tbody>
        {% for si in doc.doc_list %}
        <tr>
            <td style="padding: 6px;">{{ si.name }}</td>
            <td style="padding: 6px;">{{ si.customer }}</td>
            <td style="padding: 6px;">{{ frappe.utils.formatdate(si.posting_date) }}</td>
            <td style="padding: 6px;">{{ frappe.utils.fmt_money(si.grand_total, symbol=si.currency) }}</td>
            <td style="padding: 6px;">
                <a href="{{ frappe.utils.get_url('/app/sales-invoice/' + si.name) }}" target="_blank">View</a>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
<br>
<p>Thank you.</p>
