import frappe

import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging
import argparse
import json
import requests
import google.auth.transport.requests

from google.oauth2 import service_account

PROJECT_ID = 'smart-fm-43fa5'
BASE_URL = 'https://fcm.googleapis.com'
FCM_ENDPOINT = 'v1/projects/' + PROJECT_ID + '/messages:send'
FCM_URL = BASE_URL + '/' + FCM_ENDPOINT
SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']

class FirebaseNotification():
    def __init__(self):
        self.path_key = frappe.local.conf.firebase_key
        self.auth_token = self.get_access_token()

    def get_access_token(self):
        """Retrieve a valid access token that can be used to authorize requests.

        :return: Access token.
        """
        credentials = service_account.Credentials.from_service_account_file(self.path_key, scopes=SCOPES)
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        return credentials.token

    def send_fcm_message(self, fcm_message):
        """Send HTTP request to FCM with given message.

        Args:
            fcm_message: JSON object that will make up the body of the request.
        """
        # [START use_access_token]
        headers = {
            'Authorization': 'Bearer ' + self.get_access_token(),
            'Content-Type': 'application/json; UTF-8',
        }
        # [END use_access_token]
        resp = requests.post(FCM_URL, data=json.dumps(fcm_message), headers=headers)

        if resp.status_code == 200:
            return True
        else:
            return False

    def send_message(self, message, token="", send_all=False, title="Smart FM"):
        if not token and not send_all:
            return
        
        if token:
            msg = {
                "message":{
                    "token":token,
                    "notification":{
                        "body": message,
                        "title": title
                    }
                }
            }

            return self.send_fcm_message(msg)