import requests
import json
import os
from io import BytesIO
from datetime import datetime
import random
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

username = os.environ.get("NAUKRI_USERNAME")
password = os.environ.get("NAUKRI_PASSWORD")
file_id = os.environ.get("GOOGLE_DRIVE_FILE_ID")
form_key = os.environ.get("NAUKRI_FORM_KEY")
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

    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })

    # Step 1: Visit homepage
    print("Visiting homepage...")
    s.get("https://www.naukri.com/", timeout=30)
    time.sleep(3)

    # Step 2: Visit login page
    print("Visiting login page...")
    s.get("https://www.naukri.com/nlogin/login", timeout=30)
    time.sleep(2)

    # Step 3: Login with updated payload and headers
    print("Logging in...")
    login_payload = {
        "username": username,
        "password": password,
        "grantType": "PASSWORD",
        "appId": 105,
        "itm": "glblsrch_logins",
        "additionalInfo": {}
    }

    r = s.post(
        "https://www.naukri.com/central-login-services/v1/login",
        headers={
            "accept": "application/json",
            "appid": "105",
            "clientid": "d3skt0p",
            "content-type": "application/json",
            "systemid": "jobseeker",
            "x-requested-with": "XMLHttpRequest",
            "origin": "https://www.naukri.com",
            "referer": "https://www.naukri.com/nlogin/login",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        },
        json=login_payload,
        timeout=30
    )

    print("Login status:", r.status_code)
    if r.status_code != 200:
        print("Login error response:", r.text[:500])
        r.raise_for_status()

    # Extract token
    token = None
    for cookie_name in ["nauk_at", "nkSso", "nauk_sso"]:
        token = s.cookies.get(cookie_name)
        if token:
            print(f"Token from cookie '{cookie_name}': {token[:30]}...")
            break

    if not token:
        try:
            login_data = r.json()
            token = (
                login_data.get("loginData", {}).get("token") or
                login_data.get("token") or
                login_data.get("data", {}).get("token")
            )
            print("Token from response body:", bool(token))
        except Exception as e:
            print("Could not parse login response:", e)

    if not token:
        raise ValueError("Login succeeded but no token found. Check cookie names.")

    time.sleep(2)

    # Step 4: Download PDF from Google Drive
    print("Downloading resume from Google Drive...")
    drive_session = requests.Session()
    drive_session.verify = False

    res = drive_session.get(
        f"https://drive.google.com/uc?export=download&id={file_id}",
        allow_redirects=True,
        timeout=60
    )

    # Handle large file confirmation
    if b"confirm=" in res.content or b"virus scan warning" in res.content.lower():
        confirm_token = None
        for key, value in res.cookies.items():
            if key.startswith("download_warning"):
                confirm_token = value
                break
        if confirm_token:
            res = drive_session.get(
                f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm_token}",
                timeout=60
            )

    res.raise_for_status()
    print("PDF size:", len(res.content), "bytes")

    if len(res.content) < 1000:
        raise ValueError(f"Downloaded file too small, likely not a valid PDF: {res.content[:200]}")

    # Step 5: Upload resume
    print("Uploading resume to Naukri...")
    upload_resp = s.post(
        "https://filevalidation.naukri.com/file",
        headers={
            "accept": "application/json",
            "appid": "105",
            "origin": "https://www.naukri.com",
            "referer": "https://www.naukri.com/",
            "systemid": "fileupload",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
        },
        files={"file": (final_filename, BytesIO(res.content), "application/pdf")},
        data={
            "formKey": form_key,
            "fileName": final_filename,
            "uploadCallback": "true",
            "fileKey": FILE_KEY
        },
        verify=False,
        timeout=60
    )
    print("Upload status:", upload_resp.status_code)
    if upload_resp.status_code != 200:
        print("Upload error:", upload_resp.text[:300])
    upload_resp.raise_for_status()
    time.sleep(2)

    # Step 6: Get profile ID
    print("Fetching dashboard...")
    d = s.get(
        "https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/dashboard",
        headers={
            "accept": "application/json",
            "appid": "105",
            "clientid": "d3skt0p",
            "systemid": "Naukri",
            "authorization": f"Bearer {token}",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        },
        timeout=30
    )
    d.raise_for_status()
    dashboard_data = d.json()
    profile_id = dashboard_data.get("dashBoard", {}).get("profileId")
    print("Profile ID:", profile_id)

    if not profile_id:
        print("Dashboard response:", json.dumps(dashboard_data, indent=2)[:500])
        raise ValueError("Could not retrieve profile ID.")

    # Step 7: Update resume
    print("Updating resume...")
    payload = {
        "textCV": {
            "formKey": form_key,
            "fileKey": FILE_KEY,
            "textCvContent": None
        }
    }

    resp = s.post(
        f"https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/profiles/{profile_id}/advResume",
        headers={
            "accept": "application/json",
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "origin": "https://www.naukri.com",
            "referer": "https://www.naukri.com/mnjuser/profile?id=&altresid",
            "x-http-method-override": "PUT",
            "x-requested-with": "XMLHttpRequest",
            "appid": "105",
            "clientid": "d3skt0p",
            "systemid": "105",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        },
        data=json.dumps(payload),
        timeout=30
    )

    print("Update status:", resp.status_code)
    print("Update response:", resp.text[:300])

    if resp.status_code == 200:
        return {"success": True, "message": "Resume updated successfully"}
    else:
        return {"success": False, "message": f"Failed with status {resp.status_code}: {resp.text[:200]}"}


print(update_resume())
