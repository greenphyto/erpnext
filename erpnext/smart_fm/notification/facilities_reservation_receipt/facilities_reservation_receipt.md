<p>Dear {{doc.full_name}},</p>
<p>We are pleased to confirm your reservation for the facilities at Greenphyto. Below are the details of your booking:
<br>
<table>
    <tr><td>Facility Name</td><td>: <b>{{ doc.service }}</b></td></tr>
    {% if not doc.all_day and not doc.multi_days %}
        <tr><td>Date</td><td>: {{ frappe.utils.format_date(doc.from_date) }}</td></tr>
        <tr><td>Time</td><td>: {{ doc.start_time }} - {{ doc.end_time }}</td></tr>
    {% elif doc.multi_days %}
        <tr><td>Dates</td><td>: {{ frappe.utils.format_date(doc.from_date) }} - {{ frappe.utils.format_date(doc.to_date) }}</td></tr>
    {% else %}
        <tr><td>Date</td><td>: {{ frappe.utils.format_date(doc.from_date) }} (All Day)</td></tr>
    {% endif %}
    <tr><td>Purpose of Use</td><td>: {{ doc.purpose }}</td></tr>
    <tr><td>Number of Participants</td><td>: {{ doc.participants }}</td></tr>
    <tr><td>Special Requests</td><td>: {{ doc.special_requests }}</td></tr>
</table>
<br>
<p>Please ensure that all usage complies with our facility guidelines. If you have any further questions or require additional assistance, do not hesitate to contact us.
Thank you for choosing Greenphyto for your [event/meeting/workshop]. We look forward to hosting you.</p>
<br>
<p>Warm regards,</p>
<p>{{ frappe.db.get_value("User", frappe.session.user, "full_name") }}</p>
<p>Building Management</p>
<p>Greenphyto Facilities Team</p>