from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.gp_erp.notification.raw_material_more_than_1_year.raw_material_more_than_1_year import (
	AUTO_WRITE_OFF_THRESHOLD,
	auto_write_off_batch,
	notify_raw_material_more_than_1_year,
	split_batches,
)


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

	def test_dry_run_does_not_mutate(self):
		batches = [_batch("B-1", 10.0), _batch("B-2", 250.0)]

		with patch(
			"erpnext.gp_erp.notification.raw_material_more_than_1_year."
			"raw_material_more_than_1_year.get_aged_raw_material_batches",
			return_value=batches,
		), patch(
			"erpnext.gp_erp.notification.raw_material_more_than_1_year."
			"raw_material_more_than_1_year.get_batch_qty",
			return_value=[{"warehouse": "WH 1", "qty": 5}],
		) as mock_qty, patch(
			"erpnext.gp_erp.notification.raw_material_more_than_1_year."
			"raw_material_more_than_1_year.make_stock_entry"
		) as mock_make_se, patch(
			"frappe.db.set_value"
		) as mock_set_value, patch(
			"frappe.get_doc"
		) as mock_get_doc:
			result = notify_raw_material_more_than_1_year(dry_run=True)

		self.assertEqual({b.name for b in result.written_off}, {"B-1"})
		self.assertEqual({b.name for b in result.notified}, {"B-2"})
		self.assertTrue(result.dry_run)

		mock_qty.assert_called_once()
		mock_make_se.assert_not_called()
		mock_set_value.assert_not_called()
		mock_get_doc.assert_not_called()

	def test_live_run_writes_off_and_notifies(self):
		batches = [_batch("B-low", 10.0), _batch("B-high", 250.0)]

		with patch(
			"erpnext.gp_erp.notification.raw_material_more_than_1_year."
			"raw_material_more_than_1_year.get_aged_raw_material_batches",
			return_value=batches,
		), patch(
			"erpnext.gp_erp.notification.raw_material_more_than_1_year."
			"raw_material_more_than_1_year.get_batch_qty",
			return_value=[{"warehouse": "WH 1", "qty": 5}],
		), patch(
			"erpnext.gp_erp.notification.raw_material_more_than_1_year."
			"raw_material_more_than_1_year.make_stock_entry"
		) as mock_make_se, patch(
			"frappe.db.set_value"
		) as mock_set_value, patch(
			"frappe.get_doc"
		) as mock_get_doc:
			result = notify_raw_material_more_than_1_year(dry_run=False)

		# only the low-value batch is written off
		mock_make_se.assert_called_once()
		_, kwargs = mock_make_se.call_args
		self.assertEqual(kwargs["item_code"], "ITEM-B-low")
		self.assertEqual(kwargs["qty"], 5)
		self.assertEqual(kwargs["purpose"], "Material Issue")

		mock_set_value.assert_called_once_with("Batch", "B-low", "disabled", 1)

		# high-value batch goes to the notification
		mock_get_doc.assert_called_once_with("Notification", "Raw Material more than 1 year")
		sent_doc = mock_get_doc.return_value.send.call_args.args[0]
		self.assertEqual({b.name for b in sent_doc.doc_list}, {"B-high"})
		self.assertEqual(sent_doc.total_stock_value, 250.0)

		self.assertEqual({b.name for b in result.written_off}, {"B-low"})
		self.assertEqual({b.name for b in result.notified}, {"B-high"})

	def test_dry_run_single_batch_helper(self):
		batch = _batch("B-1", 10.0)

		with patch(
			"erpnext.gp_erp.notification.raw_material_more_than_1_year."
			"raw_material_more_than_1_year.get_batch_qty",
			return_value=[{"warehouse": "WH 1", "qty": 5}],
		), patch(
			"erpnext.gp_erp.notification.raw_material_more_than_1_year."
			"raw_material_more_than_1_year.make_stock_entry"
		) as mock_make_se, patch(
			"frappe.db.set_value"
		) as mock_set_value:
			auto_write_off_batch(batch, dry_run=True)

		mock_make_se.assert_not_called()
		mock_set_value.assert_not_called()
