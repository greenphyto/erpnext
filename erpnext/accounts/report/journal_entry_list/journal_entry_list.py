import frappe, json
from frappe import _

def execute(filters=None):

    # get column
    column = [
        {"label": _("Name"),    "fieldtype":"Data",    "fieldname": "name",            "width": 100},
		{"label": _("Date"),    "fieldtype":"Date",    "fieldname": "posting_date",    "width": 100},
        {"label": _("Status"),  "fieldtype":"Data",    "fieldname": "docstatus",       "width": 100}
    ]

    # get data
    requested_column = [
        
    ]
    data = frappe.db.sql("""
        SELECT 
            a.*
        FROM
            (SELECT 
                j.name,
                    j.posting_date,
                    IF(j.docstatus = 0, 'Draft', IF(j.docstatus = 1, 'Submitted', 'Cancelled')) as docstatus,
                    j.voucher_type
            FROM
                `tabJournal Entry` j UNION ALL SELECT 
                d.deleted_name,
                    d.document_date,
                    'Deleted' AS docstatus,
                    d.data
            FROM
                `tabDeleted Document` d
            WHERE
                d.deleted_doctype = 'Journal Entry') a
        ORDER BY a.name DESC
    """, as_dict=1)

    # process
    final_data = []
    for d in data:
        if d.docstatus == 3:
            dt = json.loads(d.voucher_type)
            final_data.append(dt)
        else:
            final_data.append(d)
    return column, final_data