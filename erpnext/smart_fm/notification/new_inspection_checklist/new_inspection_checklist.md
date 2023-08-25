<h3>{{doc.doctype}}</h3>

<p>A new request ({{ frappe.utils.get_link_to_form(doc.doctype, doc.name) }}) has been made.</p>
<p>We will inform you if any further updates</p>

{{ frappe.render_template("templates/end_support.html", {}) }}