<p>Dear Team,</p>

<p>
    The system detected that request <strong>{{ doc.name }}</strong> 
    (created on {{ doc.get_formatted("creation") }}) 
    <strong>failed to sync to FOMS</strong>.
</p>

<p>
    Please review the issue and re-trigger the synchronization using the link below:
</p>

<p style="margin: 20px 0;">
    <a href="{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}" 
       style="background-color: #ff4d4f; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold;">
        Check in ERPNext
    </a>
</p>

<br>
<hr style="border: none; border-top: 1px solid #eaeaea;">
<p style="font-size: 11px; color: #8c8c8c;">
    This is an automated message sent by the ERPNext Notification System. Please do not reply directly to this email.
</p>