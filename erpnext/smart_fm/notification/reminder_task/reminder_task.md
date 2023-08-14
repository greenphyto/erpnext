<p>Your Task <b>{{doc.name}}</b> must be completed within {{ get_day_diff("", doc.date) }} days ({{doc.date}})</p>
<br>
<u><a href="{{ frappe.get_url('/app/todo/'+doc.name) }}">Go to the Task</a></u>
<br>
<br>
<u><a href="{{ doc.get_turn_off_reminder_url() }}">Turn off reminder</a></u>