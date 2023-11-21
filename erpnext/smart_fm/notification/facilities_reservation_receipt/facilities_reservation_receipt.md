<p>Dear {{doc.full_name}},</p>
<br>
<p>We are pleased to confirm your reservation for the facilities at Greenphyto. Below are the details of your booking:
<br>
<table>
    <tr><td>Facility Name:</td><td>{{ doc.service }}</td></tr>
    <tr><td>Time:</td><td>{{ doc.service }}</td></tr>
    <tr><td>Purpose of Use:</td><td>{{ doc.service }}</td></tr>
    <tr><td>Number of Participants:</td><td>{{ doc.service }}</td></tr>
    <tr><td>Special Requests:</td><td>{{ doc.service }}</td></tr>
</table>
<p>Please ensure that all usage complies with our facility guidelines. If you have any further questions or require additional assistance, do not hesitate to contact us.
Thank you for choosing Greenphyto for your [event/meeting/workshop]. We look forward to hosting you.</p>
<br>
<p>Warm regards,</p>
<p>{{ frappe.db.get_value("User", frappe.session.user, "full_name") }}</p>
<p>Building Management Staff</p>
<p>Greenphyto Facilities Team</p>