from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.gp_erp.notification.raw_material_more_than_1_year.raw_material_more_than_1_year import (
	AUTO_WRITE_OFF_THRESHOLD,
	auto_write_off_batches,
	get_aged_raw_material_batches,
	notify_raw_material_more_than_1_year,
	split_batches,
)

MODULE = "erpnext.gp_erp.notification.raw_material_more_than_1_year.raw_material_more_than_1_year"


def _batch(name, stock_value):
	return frappe._dict(
		{
			"name": name,
			"item": f"ITEM-{name}",
			"item_name": f"Item {name}",
			"item_group": "Raw Material",
			"manufacturing_date": "2020-01-01",
			"batch_qty": 5,
			"stock_uom": "Nos",
			"stock_value": stock_value,
		}
	)


class TestRawMaterialMoreThan1Year(FrappeTestCase):
	def test_split_batches_by_threshold(self):
		below_1 = _batch("B-1", 10.0)
		below_2 = _batch("B-2", 99.99)
		boundary = _batch("B-3", 100.0)
		above = _batch("B-4", 250.0)

		write_off, notify = split_batches([below_1, below_2, boundary, above])

		write_off_names = {b.name for b in write_off}
		notify_names = {b.name for b in notify}

		self.assertEqual(write_off_names, {"B-1", "B-2"})
		self.assertEqual(notify_names, {"B-3", "B-4"})

		self.assertEqual(AUTO_WRITE_OFF_THRESHOLD, 100.0)
		for b in write_off:
			self.assertLess(b.stock_value, AUTO_WRITE_OFF_THRESHOLD)
		for b in notify:
			self.assertGreaterEqual(b.stock_value, AUTO_WRITE_OFF_THRESHOLD)

	def test_aging_uses_last_audited_over_manufacturing_date(self):
		captured = {}

		def fake_get_all(doctype, filters=None, fields=None, order_by=None, **kwargs):
			if doctype == "Batch":
				captured["filters"] = filters
				captured["order_by"] = order_by
				return []
			return []

		with patch("frappe.get_all", side_effect=fake_get_all):
			result = get_aged_raw_material_batches()

		self.assertEqual(result, [])

		# the age reference must be COALESCE(last_audited, manufacturing_date)
		age_key = "ifnull(last_audited, manufacturing_date)"
		self.assertIn(age_key, captured["filters"])
		self.assertEqual(captured["filters"][age_key][0], "<=")

		# plain manufacturing_date must NOT be used as the aging filter anymore
		self.assertNotIn("manufacturing_date", captured["filters"])

		self.assertEqual(captured["order_by"], f"{age_key} asc")

	def test_dry_run_does_not_mutate(self):
		batches = [_batch("B-1", 10.0), _batch("B-2", 250.0)]

		with patch(
			f"{MODULE}.get_aged_raw_material_batches",
			return_value=batches,
		), patch(
			f"{MODULE}.get_write_off_stock",
			return_value={"Comp A": [frappe._dict(batch="B-1", warehouse="WH 1", qty=5)]},
		) as mock_stock, patch(
			f"{MODULE}.make_scrap_stock_entry"
		) as mock_make_se, patch(
			"frappe.db.set_value"
		) as mock_set_value, patch(
			"frappe.get_doc"
		) as mock_get_doc:
			result = notify_raw_material_more_than_1_year(dry_run=True)

		self.assertEqual({b.name for b in result.written_off}, {"B-1"})
		self.assertEqual({b.name for b in result.notified}, {"B-2"})
		self.assertTrue(result.dry_run)

		# stock lookup is allowed (read-only) but nothing is mutated
		mock_make_se.assert_not_called()
		mock_set_value.assert_not_called()
		mock_get_doc.assert_not_called()

	def test_live_run_single_stock_entry_per_company(self):
		batches = [_batch("B-low1", 10.0), _batch("B-low2", 20.0), _batch("B-high", 250.0)]

		# both low-value batches live in the same company -> one Stock Entry
		company_rows = {
			"Comp A": [
				frappe._dict(batch="B-low1", item_code="ITEM-B-low1", warehouse="WH 1", qty=5, uom="Nos"),
				frappe._dict(batch="B-low2", item_code="ITEM-B-low2", warehouse="WH 2", qty=3, uom="Nos"),
			]
		}

		with patch(
			f"{MODULE}.get_aged_raw_material_batches",
			return_value=batches,
		), patch(
			f"{MODULE}.get_write_off_stock",
			return_value=company_rows,
		), patch(
			f"{MODULE}.make_scrap_stock_entry"
		) as mock_make_se, patch(
			"frappe.db.set_value"
		) as mock_set_value, patch(
			"frappe.get_doc"
		) as mock_get_doc:
			result = notify_raw_material_more_than_1_year(dry_run=False)

		# exactly ONE Stock Entry for the company (not one per batch)
		mock_make_se.assert_called_once()
		args, _ = mock_make_se.call_args
		self.assertEqual(args[0], "Comp A")
		self.assertEqual({r.batch for r in args[1]}, {"B-low1", "B-low2"})

		# both scrapped batches get disabled
		disabled = {c.args[0:3] for c in mock_set_value.call_args_list}
		self.assertEqual(disabled, {("Batch", "B-low1", "disabled"), ("Batch", "B-low2", "disabled")})

		# high-value batch goes to the notification
		mock_get_doc.assert_called_once_with("Notification", "Raw Material more than 1 year")
		sent_doc = mock_get_doc.return_value.send.call_args.args[0]
		self.assertEqual({b.name for b in sent_doc.doc_list}, {"B-high"})
		self.assertEqual(sent_doc.total_stock_value, 250.0)

		self.assertEqual({b.name for b in result.written_off}, {"B-low1", "B-low2"})
		self.assertEqual({b.name for b in result.notified}, {"B-high"})

	def test_live_run_one_entry_per_company(self):
		company_rows = {
			"Comp A": [frappe._dict(batch="B-1", item_code="I1", warehouse="WH 1", qty=5, uom="Nos")],
			"Comp B": [frappe._dict(batch="B-2", item_code="I2", warehouse="WH 2", qty=2, uom="Nos")],
		}

		with patch(
			f"{MODULE}.get_write_off_stock",
			return_value=company_rows,
		), patch(
			f"{MODULE}.make_scrap_stock_entry"
		) as mock_make_se, patch(
			"frappe.db.set_value"
		) as mock_set_value:
			auto_write_off_batches([_batch("B-1", 10.0), _batch("B-2", 20.0)], dry_run=False)

		# two companies -> two Stock Entries
		self.assertEqual(mock_make_se.call_count, 2)
		self.assertEqual(mock_set_value.call_count, 2)

	def test_dry_run_batches_helper(self):
		company_rows = {
			"Comp A": [frappe._dict(batch="B-1", item_code="I1", warehouse="WH 1", qty=5, uom="Nos")]
		}

		with patch(
			f"{MODULE}.get_write_off_stock",
			return_value=company_rows,
		), patch(
			f"{MODULE}.make_scrap_stock_entry"
		) as mock_make_se, patch(
			"frappe.db.set_value"
		) as mock_set_value:
			auto_write_off_batches([_batch("B-1", 10.0)], dry_run=True)

		mock_make_se.assert_not_called()
		mock_set_value.assert_not_called()
