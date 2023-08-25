<h3>{{ doc.doctype }}</h3>

<p>The request ({{ frappe.utils.get_link_to_form(doc.doctype, doc.name) }}) has been {{doc.workflow_state}} by building management.</p>

{{ frappe.render_template("templates/end_support.html", {}) }}