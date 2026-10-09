import frappe
from frappe import _
from frappe.utils import flt, getdate, today


@frappe.whitelist()
def check_unposted_depr_before_disposal(asset_name, disposal_date=None):
    """Check unposted depreciation entries before asset disposal.
    Returns dict with unposted_count, disposal_date, and future_posted list.
    """
    asset = frappe.get_doc("Asset", asset_name)
    if not disposal_date:
        disposal_date = asset.disposal_date or today()
    disposal_date = getdate(disposal_date)

    unposted_count = 0
    future_posted = []

    finance_books = asset.get("finance_books") or []
    for fb in finance_books:
        fb_name = fb.name
        schedules = frappe.db.sql(
            """
			SELECT schedule_date, journal_entry, depreciation_amount
			FROM `tabDepreciation Schedule`
			WHERE parent=%s AND finance_book_id=%s AND (journal_entry IS NULL OR journal_entry = '')
			AND schedule_date <= %s
			""",
            (asset.name, fb.idx, disposal_date),
            as_dict=True,
        )
        unposted_count += len(schedules)

        future = frappe.db.sql(
            """
			SELECT journal_entry, schedule_date, depreciation_amount
			FROM `tabDepreciation Schedule`
			WHERE parent=%s AND finance_book_id=%s AND journal_entry IS NOT NULL AND journal_entry != ''
			AND schedule_date > %s
			""",
            (asset.name, fb.idx, disposal_date),
            as_dict=True,
        )
        future_posted.extend(future)

    return {
        "unposted_count": unposted_count,
        "disposal_date": disposal_date,
        "future_posted": future_posted,
    }


def check_future_posted_depreciation(asset, disposal_date):
    """Return list of posted depreciation entries after disposal_date."""
    future_posted = []
    schedules = asset.get("schedules") or []
    if schedules:
        for row in schedules:
            if row.get("journal_entry") and getdate(row.get("schedule_date")) > getdate(disposal_date):
                future_posted.append(
                    {
                        "journal_entry": row.get("journal_entry"),
                        "schedule_date": row.get("schedule_date"),
                        "depreciation_amount": row.get("depreciation_amount"),
                    }
                )
        return future_posted
    finance_books = asset.get("finance_books") or []
    for fb in finance_books:
        future = frappe.db.sql(
            """
			SELECT journal_entry, schedule_date, depreciation_amount
			FROM `tabAsset Depreciation Schedule`
			WHERE parent=%s AND finance_book_id=%s AND journal_entry
			AND schedule_date > %s AND is_cancelled = 0
			""",
            (asset.name, fb.idx, disposal_date),
            as_dict=True,
        )
        future_posted.extend(future)
    return future_posted


def check_unposted_depreciation_entries(asset, disposal_date, finance_book=None):
    """Return list of unposted depreciation entries up to disposal_date."""
    conditions = ""
    params = [asset.name, disposal_date]
    if finance_book:
        conditions = "AND finance_book_id=%s"
        params.append(finance_book)

    return frappe.db.sql(
        """
		SELECT schedule_date, depreciation_amount
		FROM `tabAsset Depreciation Schedule`
		WHERE parent=%s AND NOT journal_entry AND schedule_date <= %s
		{conditions}
		""".format(conditions=conditions),
        tuple(params),
        as_dict=True,
    )


def get_month_year(date):
    date = getdate(date)
    return f"{date.month:02d} {date.year}"


def get_depreciable_assets(date, asset_category=None):
    filters = {
        "docstatus": 1,
        "status": ("not in", ["Scrapped", "Sold", "Capitalized", "Decapitalized"]),
        "calculate_depreciation": 1,
    }
    if asset_category:
        filters["asset_category"] = ("in", asset_category)
    return frappe.get_all("Asset", filters=filters, pluck="name")


def _warn_unposted_depreciation(asset, disposal_date, finance_book=None):
    unposted = check_unposted_depreciation_entries(asset, disposal_date, finance_book)
    if unposted:
        frappe.msgprint(
            _(
                "There are {0} unposted depreciation entry/entries on or before the disposal date {1}. "
                "Only posted depreciation entries are recognized in the disposal journal. "
                "Please post outstanding depreciation entries first (Create Depreciation Entry) "
                "to ensure Accumulated Depreciation and Gain/Loss on Disposal are accurate."
            ).format(frappe.bold(unposted), frappe.bold(disposal_date)),
            title=_("Unposted Depreciation Entries"),
            indicator="orange",
            alert=True,
        )
