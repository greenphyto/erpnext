<h3>{{ doc.doctype }}</h3>

<p>The request ({{ frappe.utils.get_link_to_form(doc.doctype, doc.name) }}) has been {{doc.workflow_state}} by building management.</p>

{% if doc.bm_comment %}
<p>BM's Comment:</p>
<img src="{{ frappe.utils.get_url(doc.bm_attachment) }}" style="max-width:400px;">
<p>{{doc.bm_comment}}</p>
{% endif %}

{{ frappe.render_template("templates/end_support.html", {}) }}