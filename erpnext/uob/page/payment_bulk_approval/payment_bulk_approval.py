import frappe
from frappe.model.workflow import get_transitions
from frappe.utils import flt

@frappe.whitelist()
def get_data(start=0, page_length=20, filters=None):
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

    set_flt = [["status", "=", "Pending"]]
    posting_date_from = filters.get('posting_date_from')
    posting_date_to = filters.get('posting_date_to')
    if posting_date_from and posting_date_to:
        set_flt.append(["posting_date", "between", [posting_date_from, posting_date_to]])
    elif posting_date_from:
        set_flt.append(["posting_date", ">=", posting_date_from])
    elif posting_date_to:
        set_flt.append(["posting_date", "<=", posting_date_to])

    if filters.get('requested_by'):
        set_flt.append(["requested_by", "=", filters['requested_by']])
    if filters.get('bank_account'):
        set_flt.append(["bank_account", "=", filters['bank_account']])
    if filters.get('currency'):
        set_flt.append(["currency", "=", filters['currency']])
    if filters.get('approval_id'):
        set_flt.append(["name", "like", f"%{filters['approval_id']}%"])
    if flt(filters.get('amount_min')):
        set_flt.append(["total_amount", ">=", flt(filters.get('amount_min'))])
    if flt(filters.get('amount_max')):
        set_flt.append(["total_amount", "<=", flt(filters.get('amount_max'))])

    names = frappe.get_list(
        'Payment Approval',
        filters=set_flt,
        fields=['name'],
        order_by='modified desc',
        start=start,
        page_length=page_length,
    )

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

    # Totals
    total = frappe.db.count('Payment Approval', filters=set_flt)
    # Pending amount total (sum of total_amount) for the full filtered dataset
    try:
        sum_rows = frappe.db.get_all(
            'Payment Approval',
            filters=set_flt,
            fields=['sum(total_amount) as total_amount_sum']
        )
        pending_total = flt(sum_rows[0].get('total_amount_sum')) if sum_rows else 0.0
    except Exception:
        pending_total = 0.0
    has_more = start + len(results) < total
    next_start = start + len(results)
    return {
        'results': results,
        'has_more': has_more,
        'next_start': next_start,
        'total': total,
        'pending_total': pending_total,
        # If currency filter is applied, pass it back for client formatting
        'pending_currency': filters.get('currency') if isinstance(filters, dict) else None,
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
        else:
            d.db_set("selected", 0)

    # Expose to any custom server-side logic
    frappe.flags.selected_invoices = invoices
    if hasattr(doc, 'flags'):
        doc.flags.selected_invoices = invoices

    # change reject if not any invoice selected
    if not invoices and action == 'Approve':
        action = "Reject"

    return apply_workflow(doc, action)
