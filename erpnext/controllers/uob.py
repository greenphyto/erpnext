import frappe, requests, json, os
from urllib.parse import urljoin
from six import string_types
from frappe.utils import cint, flt
from requests.adapters import HTTPAdapter

class UOBAPI():
	# API
	def __init__(self, settings=None):
		self.settings = settings or frappe.get_single("UOB Integration Settings")
		self.token = ""
		self.init_request()

	def init_request(self):
		self.session = requests.Session()
		adapter = HTTPAdapter(max_retries=3)
		self.session.mount("http://", adapter)
		self.session.mount("https://", adapter)

	def update_header(self, header):
		self.session.headers.update(header)

	def get_url(self, method=""):
		if "http" not in self.settings.host:
			host = f"http://{self.settings.host}/"
		else:
			host = self.settings.host

		url = urljoin(host, method)
		return url
	
	def get_login(self):
		return
		
		# not login yet
		if self.token:
			return
		
		url = self.get_url("/TokenAuth/Authenticate")

		res = self.session.post(url, data=json.dumps({
			"userNameOrEmailAddress": self.settings.user,
			"password": self.settings.get_password("password"),
			"rememberClient":True
		}))
		if res.status_code == 200:
			data = res.json()
			if data.get("result") and data['result'].get("accessToken"):
				self.token = f"Bearer {data['result']['accessToken']}"
				self.update_header({
					"Authorization": self.token
				})

			return data

	def convert_data(self, data):
		def fix_data(data):
			if type(data) is list:
				for i, e in enumerate(data):
					if e is None:
						data[i] = ''
					else:
						fix_data(e)

			elif type(data) is dict:
				for k, v in data.items():
					if v is None:
						data[k] = ''
					else:
						fix_data(v)
		fix_data(data)
		res = json.dumps(data, default=str)
		return res
	
	def req(self, req="POST", method="", data={}, params={}, files=None, raw=False):
		if not self.settings.enable:
			return {"error":"Not enable"}
		
		url = self.get_url(method)
		self.get_login()
		if files:
			self.update_header({
				'accept': 'application/json',
			})
		else:
			self.update_header({
				'accept': 'application/json',
				'Content-Type': 'application/json',
			})

		if req == "POST":
			res = self.session.post(url, data=data, params=params, files=files)
		elif req == "DELETE":
			res = self.session.delete(url, data=data, params=params)
		else:
			res = self.session.get(url, data=data, params=params)

		self.last_result = res
		self.request_detail = {
			"host":self.settings.host,
			"url":url,
			"method":req
		}

		try:
			self.request_detail['data'] = json.loads(data)
		except:
			pass

		# self.update_log()

		if frappe.flags.in_test:
			print(data)
			print(res.status_code)
			print(res.text)

		result = {
			'status_code':res.status_code
		}
		if raw:
			return res
		try:
			temp = res.json()
			result["result"] = temp
			if "error" in temp and temp['error']:
				print("ERROR: ", temp['error'])

			return result
		except:
			result["result"] =  res.text
			return result
		
	def download_bank_tx(self, fname=""):
		# if not fname, download latest
		url = self.get_url("/bank/download")
		dest = self.settings.folder_out
		res = self.req("GET", url, params={"fname":fname,"dest":dest})
		return res

	def get_file_list(self, limit=10):
		url = self.get_url("/file/list")
		dest = self.settings.folder_out
		res = self.req("GET", url, params={"limit":limit, "dest":dest})
		return res

	def upload_bank_tx(self, file_path, filename):
		if not os.path.exists(file_path):
			return {"error": "File not exist!"}

		with open(file_path, "rb") as f:
			url = self.get_url("/bank/upload")
			dest = self.settings.folder_in
			files = {
				"file": (filename, f),
				'dest': (None, dest) 
			}
			res = self.req("POST", url, files=files)
			return res

import xml.etree.ElementTree as ET
from datetime import datetime
from xml.dom import minidom

def create_payment_xml(invoices, debtor_info, filepath=""):
	# Namespace definitions
	ns = {
		'': 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.03',
		'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
	}
	
	# Register namespaces
	for prefix, uri in ns.items():
		ET.register_namespace(prefix, uri)
	
	# Create root element
	root = ET.Element('Document', attrib={
		'xmlns': ns[''],
		'xmlns:xsi': ns['xsi']
	})
	
	# Create CstmrCdtTrfInitn element
	cstmr_cdt_trf_initn = ET.SubElement(root, 'CstmrCdtTrfInitn')
	
	# Create Group Header
	grp_hdr = ET.SubElement(cstmr_cdt_trf_initn, 'GrpHdr')
	ET.SubElement(grp_hdr, 'MsgId').text = debtor_info["msg_id"].replace(".xml", "")
	ET.SubElement(grp_hdr, 'CreDtTm').text = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.00')
	ET.SubElement(grp_hdr, 'NbOfTxs').text = str(len(invoices))
	total_amount = sum(invoice['amount'] for invoice in invoices)
	ET.SubElement(grp_hdr, 'CtrlSum').text = f"{total_amount:.2f}"
	
	initg_pty = ET.SubElement(grp_hdr, 'InitgPty')
	initg_pty_id = ET.SubElement(initg_pty, 'Id')
	initg_pty_org_id = ET.SubElement(initg_pty_id, 'OrgId')
	print(195, debtor_info['company_id'])
	ET.SubElement(initg_pty_org_id, 'BICOrBEI').text = debtor_info['company_id']
	
	# Create Payment Information
	pmt_inf = ET.SubElement(cstmr_cdt_trf_initn, 'PmtInf')
	ET.SubElement(pmt_inf, 'PmtInfId').text = f"{datetime.now().strftime('%Y%m%d')}-{debtor_info['batch']}"
	ET.SubElement(pmt_inf, 'PmtMtd').text = debtor_info['type']
	
	pmt_tp_inf = ET.SubElement(pmt_inf, 'PmtTpInf')
	svc_lvl = ET.SubElement(pmt_tp_inf, 'SvcLvl')
	ET.SubElement(svc_lvl, 'Cd').text = debtor_info['method']
	if debtor_info['property']:
		svc_lvl = ET.SubElement(pmt_tp_inf, 'LclInstrm')
		ET.SubElement(svc_lvl, 'Cd').text = debtor_info['property']

	ctgy_purp = ET.SubElement(pmt_tp_inf, 'CtgyPurp')
	ET.SubElement(ctgy_purp, 'Cd').text = debtor_info['purpose']
	
	ET.SubElement(pmt_inf, 'ReqdExctnDt').text = datetime.now().strftime('%Y-%m-%d')
	
	# Debtor information
	dbtr = ET.SubElement(pmt_inf, 'Dbtr')
	ET.SubElement(dbtr, 'Nm').text = debtor_info['name']
	
	dbtr_pstl_adr = ET.SubElement(dbtr, 'PstlAdr')
	ET.SubElement(dbtr_pstl_adr, 'Ctry').text = 'SG' # -- not yet
	
	dbtr_id = ET.SubElement(dbtr, 'Id')
	dbtr_org_id = ET.SubElement(dbtr_id, 'OrgId')
	ET.SubElement(dbtr_org_id, 'BICOrBEI').text = debtor_info['bic']
	dbtr_othr = ET.SubElement(dbtr_org_id, 'Othr')
	ET.SubElement(dbtr_othr, 'Id').text = debtor_info["company_id"]
	
	# Debtor account
	dbtr_acct = ET.SubElement(pmt_inf, 'DbtrAcct')
	dbtr_acct_id = ET.SubElement(dbtr_acct, 'Id')
	dbtr_acct_othr = ET.SubElement(dbtr_acct_id, 'Othr')
	ET.SubElement(dbtr_acct_othr, 'Id').text = debtor_info['account_number']
	ET.SubElement(dbtr_acct, 'Ccy').text = 'SGD' # -- not yet
	ET.SubElement(dbtr_acct, 'Nm').text = f"{debtor_info['company_name']}"
	
	# Debtor agent
	dbtr_agt = ET.SubElement(pmt_inf, 'DbtrAgt')
	dbtr_agt_fin_instn_id = ET.SubElement(dbtr_agt, 'FinInstnId')
	ET.SubElement(dbtr_agt_fin_instn_id, 'BIC').text = debtor_info['bic']
	dbtr_agt_pstl_adr = ET.SubElement(dbtr_agt_fin_instn_id, 'PstlAdr')
	ET.SubElement(dbtr_agt_pstl_adr, 'Ctry').text = 'SG' # -- not yet
	
	# Create Credit Transfer Transaction Information for each invoice
	for i, invoice in enumerate(invoices, start=1):
		cdt_trf_tx_inf = ET.SubElement(pmt_inf, 'CdtTrfTxInf')
		
		# Payment ID
		pmt_id = ET.SubElement(cdt_trf_tx_inf, 'PmtId')
		ET.SubElement(pmt_id, 'InstrId').text = invoice["instruction_start"]
		ET.SubElement(pmt_id, 'EndToEndId').text = invoice["instruction_end"]
		
		# Amount
		amt = ET.SubElement(cdt_trf_tx_inf, 'Amt')
		instd_amt = ET.SubElement(amt, 'InstdAmt', attrib={'Ccy': invoice['currency']})
		instd_amt.text = f"{invoice['amount']:.2f}"
		
		# Creditor Agent
		cdtr_agt = ET.SubElement(cdt_trf_tx_inf, 'CdtrAgt')
		cdtr_agt_fin_instn_id = ET.SubElement(cdtr_agt, 'FinInstnId')
		ET.SubElement(cdtr_agt_fin_instn_id, 'BIC').text = invoice['creditor_bic']
		
		# Creditor
		cdtr = ET.SubElement(cdt_trf_tx_inf, 'Cdtr')
		ET.SubElement(cdtr, 'Nm').text = invoice['creditor_name']
		
		if invoice.get("address"):
			addr = invoice.get("address")
			cdtr_pstl_adr = ET.SubElement(cdtr, 'PstlAdr')
			cdtr_adr = ET.SubElement(cdtr_pstl_adr, 'Adr')
			ET.SubElement(cdtr_adr, 'PstCd').text = addr.get("postal_code")
			ET.SubElement(cdtr_adr, 'Ctry').text = addr.get("country")
			ET.SubElement(cdtr_adr, 'AdrLine').text = addr.get("address_line")
		
		# Creditor Account
		cdtr_acct = ET.SubElement(cdt_trf_tx_inf, 'CdtrAcct')
		cdtr_acct_id = ET.SubElement(cdtr_acct, 'Id')
		cdtr_acct_othr = ET.SubElement(cdtr_acct_id, 'Othr')
		ET.SubElement(cdtr_acct_othr, 'Id').text = invoice['creditor_account']
		ET.SubElement(cdtr_acct, 'UltmtCdtr').text = f"UltimateCreditor {i:02d}"
		
		# Purpose
		purp = ET.SubElement(cdt_trf_tx_inf, 'Purp')
		ET.SubElement(purp, 'Cd').text = debtor_info['purpose']
		
		# Related Remittance Information
		rltd_rmt_inf = ET.SubElement(cdt_trf_tx_inf, 'RltdRmtInf')
		if invoice.get("email"):
			ET.SubElement(rltd_rmt_inf, 'RmtLctnMtd').text = 'EMAL'
			ET.SubElement(rltd_rmt_inf, 'RmtLctnElctrncAdr').text = invoice['email']
		
		rmt_lctn_pstl_adr = ET.SubElement(rltd_rmt_inf, 'RmtLctnPstlAdr')
		ET.SubElement(rmt_lctn_pstl_adr, 'Nm').text = invoice['creditor_name']
		
		if invoice.get("remitence_address"):
			addr = invoice.get("remitence_address")
			rmt_adr = ET.SubElement(rmt_lctn_pstl_adr, 'Adr')
			ET.SubElement(rmt_adr, 'PstCd').text = addr.get("postal_code")
			ET.SubElement(rmt_adr, 'Ctry').text = addr.get("country")
			ET.SubElement(rmt_adr, 'AdrLine').text = addr.get("address_line")
		
		# Remittance Information
		rmt_inf = ET.SubElement(cdt_trf_tx_inf, 'RmtInf')
		ET.SubElement(rmt_inf, 'Ustrd').text = "H1:INVOICE REF\t\tAMOUNT\tCURRENCY1"
		
		# Split amount for multiple invoice lines (as in example)
		inv_amount = invoice['amount']
		ET.SubElement(rmt_inf, 'Ustrd').text = f"3:{invoice['invoice_number']}\t\t{inv_amount:.2f}\t{invoice['currency']}"
		
		strd = ET.SubElement(rmt_inf, 'Strd')
		invcee = ET.SubElement(strd, 'Invcee')
		ET.SubElement(invcee, 'Nm').text = debtor_info["name"]
	
	# Convert to XML string with pretty formatting
	xml_str = ET.tostring(root, encoding='utf-8', method='xml')
	dom = minidom.parseString(xml_str)
	pretty_xml = dom.toprettyxml(indent="    ", encoding='utf-8')
	
	xml_output = pretty_xml.decode('utf-8')
	
	# Save to file
	if filepath:
		with open(filepath, 'w') as f:
			f.write(xml_output)

	return xml_output