Background Job:
<b>{{ doc.get_method(doc.typ) }}</b>
<br>
{% if doc.issue %}
Error Time:
{{ doc.get_details(doc.typ, "creation") }}
<br>
Error Trace:
<pre style="white-space:pre-wrap;background:#0f172a;color:#e5e7eb;padding:12px;border-radius:8px;overflow:auto;max-height:380px">
{{ doc.get_details(doc.typ, "details") }}
</pre>
{% else %}
<b>Runing Now ✅</b>
<br>
Time:
{{ doc.time }}
{% endif %}
