import os
import requests
from dotenv import load_dotenv

load_dotenv()  # load .env file

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")

async def send_whatsapp_text(phone_number: str,body: str) -> bool:
    """
    Send a plain text WhatsApp message using the official Cloud API.
    This works as a session message if the user has recently messaged your business,
    OR if the number is configured as a test number in dev mode.
    """

    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        raise RuntimeError("Missing WHATSAPP_TOKEN / WHATSAPP_PHONE_NUMBER_ID / TO_PHONE_NUMBER")

    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    # if phone number doesnot automatically have country code for +91 or 91..
    if len(phone_number)<=10:
        phone_number = f'91{phone_number}'

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,  # e.g. "91XXXXXXXXXX"
        "type": "text",
        "text": {
            "preview_url": False,
            "body": body
        }
    }

    resp = requests.post(url, headers=headers, json=payload)
    print("Status:", resp.status_code)
    try:
        print("Response:", resp.json())
        if resp.status_code==200:
            return True
    except Exception:
        print("Raw response:", resp.text)
        return False
    return False


# template sender
async def send_whatsapp_template(phone_number: str, template_name: str,parameters: list):
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    # if phone number doesnot automatically have country code for +91 or 91..
    if len(phone_number)<=10:
        phone_number = f'91{phone_number}'
    
    # payload
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": { "code": "en_US" },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        { "type": "text", "text": param } for param in parameters
                    ]
                }
            ]   if parameters!=None or parameters==[] else []
        }
    }

    resp = requests.post(url, headers=headers, json=payload)
    print("Status:", resp.status_code)
    try:
        print("Response:", resp.json())
        if resp.status_code==200:
            return True
    except Exception:
        print("Raw response:", resp.text)
        return False
    return False

if __name__ == "__main__":
    # change the text to whatever you want
    s1 = send_whatsapp_text("9265803360","Hello from Python via WhatsApp Cloud API 😎")

    # template example code...
    templates = {
        'hello_world':'hello_world',
        'test' : 'test_template_1',
    }
    s2 = send_whatsapp_template("9265803360",templates["hello_world"],[])
