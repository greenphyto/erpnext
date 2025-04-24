import frappe, requests, json, os
from urllib.parse import urljoin
from six import string_types
from frappe.utils import cint, flt

class UOBAPI():
	# API
	def __init__(self, settings=None):
		self.settings = settings or frappe.get_single("UOB Integration Settings")
		print(self.settings, self.settings.as_dict())
		self.token = ""
		self.init_request()

	def init_request(self):
		self.session = requests.Session()
		self.update_header({
			'accept': 'application/json',
			'Content-Type': 'application/json',
		})

	def update_header(self, header):
		self.session.headers.update(header)

	def get_url(self, method=""):
		if "http" not in self.settings.host:
			host = f"http://{self.settings.host}/"
		else:
			host = self.settings.host

		url = urljoin(host, method)
		print(url)
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
	
	def req(self, req="POST", method="", data={}, params={}, files=None):
		if not self.settings.enable:
			return {"error":"Not enable"}
		
		url = self.get_url(method)
		self.get_login()
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

		try:
			result =  res.json()
			if "error" in result and result['error']:
				print("ERROR: ", result['error'])

			return result
		except:
			result =  res.text
			return False
		
	def download_bank_tx(self, fname):
		pass

	def get_flle_list(self, limit=10):
		url = self.get_url("/file/list")
		res = self.req("GET", url, params={"limit":limit})
		return res

	def upload_bank_tx(self, file_path):
		if not os.path.exists(file_path):
			return {"error": "File not exist!"}

		with open(file_path, "rb") as f:
			url = self.get_url("/bank/upload")
			dest = self.settings.folder_in
			files = {"file": (file_path, f, "text/csv")}
			data = {"dest": dest}
			res = self.req("POST", url, files=files, data=data)
			print(100, res.status_code)
			print(122, res.json())
	