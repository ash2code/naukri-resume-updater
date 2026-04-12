import requests
import json
from io import BytesIO
from datetime import datetime
import random
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

username = "ashokmanvisoma@gmail.com"
password = "Maanvis@292516"
file_id = "1qO4_Cc7vt52WH1ukiOJz_QQ9awZsD3Qn"
form_key = "F51f8e7e54e205"
filename = ""

def generate_file_key(length):
    chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(random.choice(chars) for _ in range(length))

def update_resume():
    today = datetime.now()
    final_filename = filename or f"resume_{today.strftime('%d_%B_%Y').lower()}.pdf"
    FILE_KEY = "U" + generate_file_key(13)

    s = requests.Session()
    s.verify = False

    r = s.post("https://www.naukri.com/central-login-services/v1/login",
        headers={"accept":"application/json","appid":"105","clientid":"d3skt0p","content-type":"application/json","systemid":"jobseeker","user-agent":"Mozilla/5.0","x-requested-with":"XMLHttpRequest"},
        json={"username": username, "password": password})
    r.raise_for_status()
    print("Login:", r.status_code)

    token = s.cookies.get("nauk_at")
    print("Token:", token[:50])

    res = requests.get(f"https://drive.google.com/uc?export=download&id={file_id}", verify=False)
    res.raise_for_status()
    print("PDF size:", len(res.content))

    upload_resp = requests.post("https://filevalidation.naukri.com/file",
        headers={"accept":"application/json","appid":"105","origin":"https://www.naukri.com","referer":"https://www.naukri.com/","systemid":"fileupload","user-agent":"Mozilla/5.0"},
        files={"file": (final_filename, BytesIO(res.content), "application/pdf")},
        data={"formKey": form_key, "fileName": final_filename, "uploadCallback": "true", "fileKey": FILE_KEY},
        verify=False)
    upload_resp.raise_for_status()
    print("Upload:", upload_resp.status_code)

    d = s.get("https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/dashboard",
        headers={"accept":"application/json","appid":"105","clientid":"d3skt0p","systemid":"Naukri","user-agent":"Mozilla/5.0","authorization":f"Bearer {token}"})
    profile_id = d.json().get("dashBoard", {}).get("profileId")
    print("Profile ID:", profile_id)

    payload = {"textCV": {"formKey": form_key, "fileKey": FILE_KEY, "textCvContent": None}}

    resp = s.post(
        f"https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/profiles/{profile_id}/advResume",
        headers={
            "accept": "application/json",
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "origin": "https://www.naukri.com",
            "referer": "https://www.naukri.com/mnjuser/profile?id=&altresid",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "x-http-method-override": "PUT",
            "x-requested-with": "XMLHttpRequest",
            "appid": "105",
            "clientid": "d3skt0p",
            "systemid": "105",
        },
        data=json.dumps(payload))

    print("Update status:", resp.status_code)
    print("Update response:", resp.text)
    return {"success": resp.status_code == 200, "message": "Resume updated successfully"}

print(update_resume())