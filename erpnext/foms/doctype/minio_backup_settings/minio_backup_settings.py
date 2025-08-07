# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, os
from minio import Minio
from minio.error import S3Error
from frappe.model.document import Document
from frappe.utils.backups import get_backup_path
from frappe.integrations.offsite_backup_utils import (
	get_chunk_site,
	get_latest_backup_file,
	send_email,
	validate_file_size,
)

class MinIOBackupSettings(Document):
	pass

class MinIO():
	def __init__(self, host, key, pwd, bucket="erp-database-backup", folder=""):
		self.host = host
		self.access_key = key
		self.secret_key = pwd
		self.folder = folder
		self.bucket = bucket

	def run(self):
		# Create a client with the MinIO server playground, its access key
		# and secret key.
		client = Minio(self.host,
			access_key=self.access_key,
			secret_key=self.secret_key,
		)

		# take backup custom
		source_file = take_backup()
		if not source_file:
			return
		
		# The destination bucket and filename on the MinIO server
		bucket_name = self.bucket
		destination_file = os.path.join(self.folder, source_file.split("/")[-1])

		# Make the bucket if it doesn't exist.
		found = client.bucket_exists(bucket_name)
		if not found:
			client.make_bucket(bucket_name)
			print("Created bucket", bucket_name)
		else:
			print("Bucket", bucket_name, "already exists")

		# # Upload the file, renaming it in the process
		client.fput_object(
			bucket_name, destination_file, source_file,
		)
		print(
			source_file, "successfully uploaded as object",
			destination_file, "to bucket", bucket_name,
		)


@frappe.whitelist()
def upload_backup():
	doc = frappe.get_doc("MinIO Backup Settings")
	if not doc.enable:
		return
	
	app = MinIO(
		doc.minio_host, 
		doc.access_key, 
		doc.get_password("secret_key"), 
		bucket=doc.bucket,
		folder=doc.folder,
	)
	app.run()

from frappe.utils.backups import new_backup
def take_backup():
	doc = frappe.get_doc("MinIO Backup Settings")
	doctype = []
	for d in doc.get("database_list").split("\n"):
		dt = d.strip()
		if dt[:3] == 'tab':
			dt = dt[3:]
		doctype.append(dt)
		
	doctype = ",".join(doctype)
	odb = new_backup(
		older_than = 2,
		ignore_files=True,
		ignore_conf=0,
		include_doctypes=doctype,
		compress=1
	)

	return odb.backup_path_db