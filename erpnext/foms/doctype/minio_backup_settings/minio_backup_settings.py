# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from minio import Minio
from minio.error import S3Error
from frappe.model.document import Document

class MinIOBackupSettings(Document):
	pass

class MinIO():
	def __init__(self, key, pwd):
		self.access_key = key
		self.secret_key = pwd

	def run(self):
		# Create a client with the MinIO server playground, its access key
		# and secret key.
		print(self.access_key, self.secret_key)
		client = Minio("minio-api.greenphyto.com",
			access_key=self.access_key,
			secret_key=self.secret_key,
		)

		# The file to upload, change this path if needed
		source_file = "/workspace/development/gp-frappe-bench/apps/erpnext/erpnext/test-text-file.txt"

		# The destination bucket and filename on the MinIO server
		bucket_name = "erp-database-backup"
		destination_file = "my-test-file.txt"

		# Make the bucket if it doesn't exist.
		found = client.bucket_exists(bucket_name)
		if not found:
			client.make_bucket(bucket_name)
			print("Created bucket", bucket_name)
		else:
			print("Bucket", bucket_name, "already exists")

		# # Upload the file, renaming it in the process
		# client.fput_object(
		# 	bucket_name, destination_file, source_file,
		# )
		print(
			source_file, "successfully uploaded as object",
			destination_file, "to bucket", bucket_name,
		)

def upload_backup():
	doc = frappe.get_doc("MinIO Backup Settings")
	app = MinIO(doc.access_key, doc.get_password("secret_key"))
	app.upload()