import frappe
from frappe.model.workflow import get_transitions
from frappe.utils import flt, getdate

CUR_DEFAULT = 'SGD'

@frappe.whitelist()
def get_data(start=0, page_length=20, filters=None):
    print(filters)
    """
    Return list of Payment Approval records in Pending state with
    key fields, invoices child rows, and available workflow transitions.
    """
    try:
        start = int(start or 0)
    except Exception:
        start = 0
    try:
        page_length = int(page_length or 20)
    except Exception:
        page_length = 20

    # Parse and compose filters
    try:
        filters = frappe.parse_json(filters) if filters else {}
    except Exception:
        filters = {}

    set_flt = {"status": "Pending"}
    posting_date_from = getdate(filters.get("posting_date_from"))
    posting_date_to = getdate(filters.get("posting_date_to"))
    if posting_date_from and posting_date_to:
        set_flt["posting_date"] = ["between", [posting_date_from, posting_date_to]]
    elif posting_date_from:
        set_flt["posting_date"] = [">=", posting_date_from]
    elif posting_date_to:
        set_flt["posting_date"] = ["<=", posting_date_to]
    if filters.get("requested_by"):
        set_flt["requested_by"] = filters["requested_by"]
    if filters.get("bank_account"):
        set_flt["bank_account"] = filters["bank_account"]
    if filters.get("currency"):
        set_flt["currency"] = filters["currency"]
    if filters.get("approval_id"):
        set_flt["name"] = ["like", f"%{filters['approval_id']}%"]
    if flt(filters.get("amount_min")):
        set_flt["total_amount"] = [">=", flt(filters["amount_min"])]
    if flt(filters.get("amount_max")):
        if "total_amount" in set_flt and isinstance(set_flt["total_amount"], list):
            set_flt["total_amount"] = [
                "between",
                [flt(filters["amount_min"]), flt(filters["amount_max"])],
            ]
        else:
            set_flt["total_amount"] = ["<=", flt(filters["amount_max"])]

    print(50, set_flt)
    names = get_payment_approval_list(filters)

    results = []
    for row in names:
        doc = frappe.get_doc('Payment Approval', row.name)
        try:
            transitions = [t.action for t in get_transitions(doc)]
        except Exception:
            transitions = []

        data = {
            'name': doc.name,
            'posting_date': doc.get('posting_date'),
            'posting_time': doc.get('posting_time') or doc.get('time'),
            'requested_by': doc.get('requested_by'),
            'payment_type': doc.get('payment_type'),
            'total_amount': doc.get('total_amount'),
            'bank_account': doc.get('bank_account'),
            'currency': doc.get('currency'),
            'transitions': transitions,
            # Minimal doc payload for details (invoices + batch + currency)
            'doc': {
                'name': doc.name,
                'currency': doc.get('currency'),
                'batch_no': doc.get('batch_no') or doc.get('batch_number') or doc.get('batch') or doc.get('batch_id'),
                'invoices': [d.as_dict() for d in (doc.get('invoices') or [])],
            },
        }
        results.append(data)

    total, pending_total = get_payment_approval_totals(filters)

    has_more = start + len(results) < total
    next_start = start + len(results)
    return {
        'results': results,
        'has_more': has_more,
        'next_start': next_start,
        'total': total,
        'pending_total': pending_total,
        # If currency filter is applied, pass it back for client formatting
        'pending_currency': (filters.get('currency') if isinstance(filters, dict) else None) or CUR_DEFAULT ,
    }

from frappe.model.workflow import apply_workflow
@frappe.whitelist()
def get_apply_workflow(docname, action, selected_invoices=None):
    """
    Apply workflow action on Payment Approval and optionally receive
    a list of selected invoice identifiers from the UI.

    The list is attached to both frappe.flags and doc.flags for
    downstream hooks/logic to consume if needed.
    """
    doc = frappe.get_doc("Payment Approval", docname)
    try:
        invoices = frappe.parse_json(selected_invoices) if selected_invoices is not None else []
    except Exception:
        invoices = []
    
    for d in doc.invoices:
        if d.invoice_no in invoices:
            d.db_set("selected", 1)
            d.selected = 1
        else:
            d.selected = 0
            d.db_set("selected", 0)
    
    # Expose to any custom server-side logic
    frappe.flags.selected_invoices = invoices
    if hasattr(doc, 'flags'):
        doc.flags.selected_invoices = invoices

    # change reject if not any invoice selected
    if not invoices and action == 'Approve':
        action = "Reject"

    return apply_workflow(doc, action)

from frappe.utils import getdate, flt, cint

from frappe.utils import getdate, flt, cint

def get_conditions(filters=None):
    """Builds SQL WHERE conditions and parameter values from filters."""

    filters = filters or {}
    conditions = []
    values = {}

    # Base condition
    conditions.append("status = %(status)s")
    values["status"] = "Pending"

    # --- Posting Date filter ---
    posting_date_from = filters.get("posting_date_from")
    posting_date_to = filters.get("posting_date_to")

    if posting_date_from and posting_date_to:
        conditions.append("posting_date BETWEEN %(date_from)s AND %(date_to)s")
        values["date_from"] = getdate(posting_date_from)
        values["date_to"] = getdate(posting_date_to)
    elif posting_date_from:
        conditions.append("posting_date >= %(date_from)s")
        values["date_from"] = getdate(posting_date_from)
    elif posting_date_to:
        conditions.append("posting_date <= %(date_to)s")
        values["date_to"] = getdate(posting_date_to)

    # --- Optional filters ---
    if filters.get("requested_by"):
        conditions.append("requested_by = %(requested_by)s")
        values["requested_by"] = filters["requested_by"]

    if filters.get("bank_account"):
        conditions.append("bank_account = %(bank_account)s")
        values["bank_account"] = filters["bank_account"]

    if filters.get("currency"):
        conditions.append("currency = %(currency)s")
        values["currency"] = filters["currency"]

    if filters.get("approval_id"):
        conditions.append("name LIKE %(approval_id)s")
        values["approval_id"] = f"%{filters['approval_id']}%"

    # --- Amount range ---
    if flt(filters.get("amount_min")) and flt(filters.get("amount_max")):
        conditions.append("total_amount BETWEEN %(amount_min)s AND %(amount_max)s")
        values["amount_min"] = flt(filters["amount_min"])
        values["amount_max"] = flt(filters["amount_max"])
    elif flt(filters.get("amount_min")):
        conditions.append("total_amount >= %(amount_min)s")
        values["amount_min"] = flt(filters["amount_min"])
    elif flt(filters.get("amount_max")):
        conditions.append("total_amount <= %(amount_max)s")
        values["amount_max"] = flt(filters["amount_max"])

    # Combine into WHERE clause
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    return where_clause, values


def get_payment_approval_list(filters=None, start=0, page_length=20):
    """Get paginated list of Payment Approval names based on dynamic filters."""
    where_clause, values = get_conditions(filters)

    start = cint(start or 0)
    page_length = cint(page_length or 20)

    query = f"""
        SELECT name
        FROM `tabPayment Approval`
        WHERE {where_clause}
        ORDER BY modified DESC
        LIMIT {page_length} OFFSET {start}
    """

    result = frappe.db.sql(query, values, as_dict=True)
    return result


def get_payment_approval_totals(filters=None):
    """Return total record count and pending amount total using same dynamic conditions."""
    where_clause, values = get_conditions(filters)

    # --- Total record count ---
    count_query = f"""
        SELECT COUNT(*) AS total
        FROM `tabPayment Approval`
        WHERE {where_clause}
    """
    total_row = frappe.db.sql(count_query, values, as_dict=True)
    total = total_row[0].get("total", 0) if total_row else 0

    # --- Sum of total_amount ---
    sum_query = f"""
        SELECT SUM(total_amount) AS total_amount_sum
        FROM `tabPayment Approval`
        WHERE {where_clause}
    """
    sum_row = frappe.db.sql(sum_query, values, as_dict=True)
    pending_total = flt(sum_row[0].get("total_amount_sum")) if sum_row else 0.0

    return total, pending_total