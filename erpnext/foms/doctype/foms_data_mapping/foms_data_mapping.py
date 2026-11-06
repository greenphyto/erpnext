# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document
from frappe.utils import now, cint

class FOMSDataMapping(Document):
	def validate(self):
		self.set_status()

	def get_data(self):
		return json.loads(self.raw_data)

	def set_status(self):
		if self.doc_type and self.doc_name:
			self.status = "Mapped"
		elif self.status in ("In Progress", "Failed"):
			# keep transient/async states set explicitly by the job lifecycle
			pass
		else:
			self.status = "Unknown"


def create_foms_data(data_type, data_name, raw, reopen=False, endpoint=""):
	name = frappe.db.exists("FOMS Data Mapping", {
		"data_type":data_type,
		"data_name":data_name,
	})

	if name:
		doc = frappe.get_doc("FOMS Data Mapping", name)
		if reopen:
			doc.doc_type = ""
			doc.doc_name = ""

		elif doc.doc_type and not frappe.db.exists(doc.doc_type, doc.doc_name):
			doc.doc_name = ""
		doc.endpoint = endpoint
	else:
		doc = frappe.new_doc("FOMS Data Mapping")
		doc.data_type = data_type
		doc.created_on = now()
		doc.endpoint = endpoint
	
	if doc.status in ("Mapped", "Failed"):
		doc.status = "Unknown"
		doc.doc_type = ""
		doc.doc_name = ""

	# a fresh/reopened request clears any previous failure trace
	doc.error_message = ""

	doc.data_name = data_name
	doc.raw_data = json.dumps(raw, default=str)
	doc.last_sync = now()

	try:
		doc.save()
	except:
		pass

	return doc

def make_in_progress(log_name, inprogress=True, commit=False):
	frappe.db.set_value("FOMS Data Mapping", log_name, "status", "In Progress" if inprogress else "Unknown")
	if commit:
		frappe.db.commit()
	return True


def mark_failed(log_name, error_message="", commit=False):
	"""Flag a log as Failed and store the error so it is visible and retried
	by the scheduler (which picks up Unknown and Failed logs)."""
	frappe.db.set_value(
		"FOMS Data Mapping",
		log_name,
		{
			"status": "Failed",
			"error_message": (error_message or "")[:1000],
		},
	)
	if commit:
		frappe.db.commit()
	return True


def reclaim_stale_in_progress(stale_minutes=30, commit=True):
	"""Reset logs stuck In Progress for too long back to Failed.

	A worker that crashes after claiming a log (status In Progress) but before
	finishing leaves it stuck: the scheduler skips In Progress, so it would
	never be retried. This releases such stale claims (based on modified time)
	so the scheduler picks them up again."""
	frappe.db.sql(
		"""
		update `tabFOMS Data Mapping`
		set status = 'Failed',
			error_message = 'Reclaimed: stuck In Progress (worker crash or lost job)'
		where status = 'In Progress'
			and modified < (NOW() - INTERVAL %s MINUTE)
		""",
		(stale_minutes,),
	)
	if commit:
		frappe.db.commit()

def update_data_result(data_type, data_name, result_name, result_doctype="", name_id=None):
	if not name_id:
		name_id = frappe.db.exists("FOMS Data Mapping", {
			"data_type":data_type,
			"data_name":data_name,
		})
		
	if name_id:
		log = frappe.get_doc("FOMS Data Mapping", name_id)
		log.doc_name = result_name
		log.doc_type = result_doctype or log.data_type
		log.save()


def should_run_now(now=False):
	"""True if the request must be executed synchronously: either the caller
	asked for it (now=1) or Manufacturing Settings disables enqueueing."""
	if cint(now):
		return True
	return bool(cint(frappe.db.get_single_value("Manufacturing Settings", "disable_enqueue_on_job_card")))

def is_in_progress(data_type, data_name):
	"""Return True if a job for this log is already running.

	Used to ignore duplicate calls while a worker is still processing the
	same request (status In Progress)."""
	return frappe.db.get_value(
		"FOMS Data Mapping",
		{"data_type": data_type, "data_name": data_name},
		"status",
	) == "In Progress"


def enqueue_foms_job(method, log_name, handler_kwargs=None, queue="default", timeout=1500):
	"""Run a FOMS endpoint handler asynchronously.

	The caller registers a FOMS Data Mapping log (status Unknown) then calls
	this helper to process it in the background: the log is flagged
	In Progress immediately (so the scheduler fallback does not pick it up),
	the handler runs in a worker, and on failure the log is marked Failed with
	the error message so the scheduler retries it later.

	The flip to In Progress is done atomically: it only succeeds if the log is
	not already In Progress. If another worker is already running this log, the
	call is ignored (returns False) so duplicate requests are not enqueued.

	`method` is a dotted path to the handler. `handler_kwargs` are the keyword
	arguments passed to that handler.
	"""
	# atomic check-and-set: claim the log only if not already In Progress
	frappe.db.sql(
		"""
		update `tabFOMS Data Mapping`
		set status = 'In Progress'
		where name = %s and status != 'In Progress'
		""",
		(log_name,),
	)
	affected = frappe.db._cursor.rowcount
	frappe.db.commit()

	# nothing updated means a worker already claimed it: ignore the duplicate
	if not affected:
		return False

	# testing / local sites have no background worker: run inline (synchronous)
	# so the job is actually executed, consistent with save_log / update_log.
	run_now = bool(frappe.conf.local_site)

	# `method` here is enqueue's own first positional arg (the dotted path to
	# run_foms_job). The handler path + its args are passed as kwargs to
	# run_foms_job using distinct names to avoid clashing with enqueue's params.
	try:
		frappe.enqueue(
			"erpnext.foms.doctype.foms_data_mapping.foms_data_mapping.run_foms_job",
			queue=queue,
			timeout=timeout,
			now=run_now,
			job_method=method,
			log_name=log_name,
			handler_kwargs=handler_kwargs or {},
		)
	except Exception:
		# could not hand the job off: release the claim so it is retried
		# instead of being stuck In Progress forever
		mark_failed(log_name, error_message=frappe.get_traceback(), commit=True)
		raise

	return True


def run_foms_job(job_method, log_name, handler_kwargs=None):
	"""Worker entrypoint: execute `job_method` and keep the log consistent.

	On success the handler is responsible for marking the log Mapped (via
	update_data_result / update_log). On failure the log is marked Failed with
	the error message so the scheduler can retry it.
	"""
	handler_kwargs = handler_kwargs or {}
	handler = frappe.get_attr(job_method)
	try:
		handler(**handler_kwargs)
		frappe.db.commit()
	except Exception as e:
		frappe.db.rollback()
		traceback = frappe.get_traceback()
		mark_failed(log_name, error_message=str(e), commit=True)
		frappe.log_error(
			message=f"{job_method}\nlog: {log_name}\n{json.dumps(handler_kwargs, default=str)}\n\n{traceback}",
			title="Failed async FOMS job",
		)