# Import/Export & Minio Upload

## Summary
Data import/export functionality including CSV file generation, MinIO-based offsite database backup upload, UOB bank file download/logging, and download link tracking.

## Commits
| Hash | Message | Date |
|------|---------|------|
| b0e32af5b7 | download and save the file log | 2025-06-26 |
| a29d8b1577 | add link download | 2025-06-23 |
| 878ec0377b | download file and create log | 2025-05-07 |
| 0a20e5da7d | make a csv file | 2025-05-05 |
| 041b79b7c7 | make a csv file | 2025-05-05 |
| 6b4eea2023 | minio uploader | 2025-01-14 |
| 0d39fe0d95 | allow import | 2024-09-24 |

## Affected Files
- erpnext/foms/doctype/minio_backup_settings/minio_backup_settings.py
- erpnext/foms/doctype/uob_file_log/uob_file_log.py
- erpnext/controllers/erp_api.py

## Flow/Logic

### 1. MinIO Backup Upload (`minio_backup_settings.py`)

#### Configuration
1. `MinIO Backup Settings` is a single doctype storing MinIO connection details:
   - `minio_host`: MinIO server endpoint.
   - `access_key`: Access key credential.
   - `secret_key`: Secret key (password field).
   - `bucket`: Target bucket name (default: "erp-database-backup").
   - `folder`: Subfolder within the bucket.
   - `enable`: Toggle to enable/disable.
   - `database_list`: Newline-separated list of doctypes to include in backup.

#### Upload Flow
1. `upload_backup()` (whitelisted) is triggered (manually or via scheduler).
2. Checks if settings are enabled; exits if not.
3. Creates an `ErpMinIO` instance with host, access key, secret key, bucket, and folder.
4. Calls `ErpMinIO.run()`:
   - Takes a database backup using `frappe.utils.backups.new_backup` with only the doctypes listed in `database_list`.
   - Creates a MinIO client connection.
   - Checks if the target bucket exists; creates it if not.
   - Uploads the backup file to the bucket with the destination path `folder/filename`.

#### Backup Selection
1. `take_backup()` reads `database_list` from settings.
2. Strips `tab` prefix from table names.
3. Calls `new_backup()` with `include_doctypes` to selectively back up only specified tables.
4. Returns the backup file path.

### 2. UOB Bank File Download & Logging (`controllers/uob.py`)

#### Sync Flow (`sync_uob_file`)
1. Called via scheduler (skips weekends and holidays).
2. Reads `UOB Integration Settings` for connection details and `last_download_date`.
3. Creates a `UOBAPI` instance and calls `download_bank_tx_bulk(above_date=latest_date)`.
4. For each file returned:
   - Creates a new `UOB File Log` document.
   - Decodes base64 file content.
   - Saves the file as a private attachment under `Home/Bank` folder.
   - Links the file to the UOB File Log.
   - Calls `sync_payment_status()` to parse XML and update payment statuses.
5. Updates `last_sync_date` and `last_file_name` in settings.

#### UOBAPI Class
- `download_bank_tx(fname)`: Downloads a single bank transaction file.
- `download_bank_tx_bulk(fname, limit, above_date)`: Downloads multiple files newer than `above_date`.
- `get_file_list(limit)`: Lists available files on the UOB server.
- `upload_bank_tx(file_path, filename)`: Uploads a payment XML file to the bank server.

### 3. CSV File Generation
1. CSV generation is used in the forecast/export context for producing downloadable data files.
2. The `csv` module with `StringIO` is used to parse and generate CSV content programmatically.
3. Generated files can be attached to documents or served as downloads.

### 4. Download Link & File Log
1. When files are downloaded from the bank, a `UOB File Log` record is created.
2. The log stores: filename, filepath, linked File document, and payment approval reference.
3. Download links are made available for users to access the raw bank files.
4. The log provides an audit trail of all bank file interactions.

## Dependencies
- MinIO Python client (`minio` package)
- UOB Integration Settings doctype
- UOB File Log doctype
- frappe.utils.backups (for database backup)
- frappe.utils.file_manager (for file storage)

## Notes
- MinIO upload only runs if `enable` is checked in settings.
- UOB sync skips weekends (Saturday/Sunday).
- Bank files are stored as private files under `Home/Bank` folder.
- The `database_list` in MinIO settings uses newline-separated doctype names; `tab` prefix is auto-stripped.
- Base64 decoding is used for bank files received from the UOB API.
- The `last_download_date` in UOB settings prevents re-downloading already processed files.
