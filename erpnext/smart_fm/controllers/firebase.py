import frappe

import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging

class FirebaseNotification():
    def __init__(self):
        path_key = frappe.local.conf.firebase_key
        cred = credentials.Certificate(path_key)
        firebase_admin.initialize_app(cred)
    
    def send_message(self, text, token, title="Smart FM"):
        message = messaging.Message(
            data={
                'title': title,
                'body': text,
            },
            token=token,
        )

        # Mengirim pesan
        response = messaging.send(message)