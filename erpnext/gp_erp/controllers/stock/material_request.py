import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.stock.doctype.material_request.material_request import MaterialRequest


class MaterialRequestGP(MaterialRequest):
    def validate(self):
        super(MaterialRequestGP, self).validate()
        self.set_is_low_amount()
        self.check_attachment()
        self.set_expense_code()

    def set_is_low_amount(self):
        raw_material_totals, general_item_totals = 0, 0
        for d in self.get("items"):
            if "Raw Material" in d.item_group or "Raw Material" == d.item_group:
                raw_material_totals += flt(d.base_net_amount)
            else:
                general_item_totals += flt(d.base_net_amount)
        forbidden = []
        if flt(raw_material_totals) < 5001:
            forbidden.append(False)
        else:
            forbidden.append(True)
        if flt(general_item_totals) < 1001:
            forbidden.append(False)
        else:
            forbidden.append(True)
        if not any(forbidden):
            self.is_low_amount = 1
            return 1
        else:
            self.is_low_amount = 0
            return 0

    def check_attachment(self):
        if self.is_new() or self.flags.ignore_mandatory:
            return
        attachments = self.get_attachments()
        if len(attachments) == 0:
            frappe.throw(_("Unable to approve due to missing attachment"))
        self.set_status(update=True)

    def get_attachments(self):
        attachments = frappe.get_all(
            "File",
            fields=["name", "file_name", "file_url", "is_private"],
            filters={"attached_to_name": self.name, "attached_to_doctype": self.doctype},
        )
        return attachments

    def set_expense_code(self):
        stock_expense = frappe.get_value("Company", self.company, "stock_received_but_not_billed")
        for d in self.get("items"):
            if frappe.get_value("Item", d.item_code, 'is_stock_item'):
                d.expense_account = stock_expense


def validate_purchase_request(doc, workflow=None, transition=None, user=None):
    user = user or frappe.session.user

    if user == "Administrator":
        return True

    condition = []
    if transition.state == "Pending Approval by Purchasing Manager":
        res = validate_purchase_request_based_user(doc, user)
        condition.append(res)

    elif transition.state == "To Amend":
        if doc.owner == user:
            condition.append(True)
        else:
            condition.append(False)

    return all(condition)


def validate_purchase_request_based_user(doc, user=None):
    if not cint(frappe.db.get_single_value("Buying Settings", "enable_specific_purchase_approval")):
        return True

    creator = doc.owner
    if user == "Administrator":
        return True

    data = frappe.get_all(
        "Purchase User Permissions List",
        filters={
            "parenttype": "Buying Settings",
            "parentfield": "purchase_approval",
            "company": doc.company,
            "requester": creator,
        },
        fields="approver",
    )
    allow_specific = False

    if not data:
        return True

    for d in data:
        if d.approver == user:
            allow_specific = True

    return allow_specific


def has_permission(doc, user, ptype="read"):
    if doc.owner == user:
        return True

    res = validate_purchase_request_based_user(doc, user)
    if not res:
        return None
    else:
        return res


def get_permission_query_conditions(user=None):
    temp = frappe.db.get_value(
        "Buying Settings",
        "Buying Settings",
        ["enable_specific_purchase_approval", "enable_filter_on_list_view"],
        as_dict=True,
    )
    if cint(temp.enable_specific_purchase_approval) == 0 or cint(temp.enable_filter_on_list_view) == 0:
        return ""

    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""

    company = frappe.db.get_value("User", user, "company_selected")

    object_user = (
        frappe.get_all(
            "Purchase User Permissions List",
            filters={
                "parenttype": "Buying Settings",
                "parentfield": "purchase_approval",
                "company": company,
                "approver": user,
            },
            pluck="requester",
        )
        or [""]
    )

    return """ (`tabMaterial Request`.`owner` in ({0}) or `tabMaterial Request`.`owner`={1})""".format(
        ", ".join([frappe.db.escape(d) for d in object_user]), frappe.db.escape(user)
    )


def confirm_workflow_action_page(doc, context=None):
    """
    Hook to customize workflow action confirmation page for Material Request.
    Adds company mismatch detection and switch company functionality.
    """
    if context is None:
        context = {}

    try:
        if frappe.get_meta(doc.get("doctype")).has_field("company"):
            doc_company = doc.get("company")
            user = frappe.form_dict.get("user") or frappe.session.user
            user_company = frappe.db.get_value("User", user, "company_selected")

            if doc_company and user_company and user_company != "ALL" and doc_company != user_company:
                context["company_mismatch"] = True
                context["doc_company"] = doc_company
                context["user_company"] = user_company
                context["current_user"] = user

                from frappe.utils.verified_command import get_signed_params

                params = get_signed_params({"user": user, "to_company": doc_company})
                context["switch_company_url"] = f"/api/method/erpnext.controllers.erp.switch_company_web?{params}"
            else:
                context["company_mismatch"] = False
        else:
            context["company_mismatch"] = False
    except Exception:
        context["company_mismatch"] = False
        frappe.log_error(frappe.get_traceback(), "Material Request - Company Mismatch Check Error")

    return context
