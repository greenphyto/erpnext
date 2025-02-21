import frappe

def get_context(context):
	# do your magic here
	doc = context.get("doc")
	if not doc:
		return
	
	vgs = []
	for d in doc.get("vegetable"):
		vgs.append(f"{d.vegetable} {d.qty} packs")
	vgs_str = doc.vegetable_packages = ", ".join(vgs) or "-"
	context['doc'].update({
		"tour_ic_name": frappe.get_value("User", doc.tour_ic, "full_name"),
		"vegetable_packages": vgs_str
	})
	return context