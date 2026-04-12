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

    # Realistic browser headers
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    })

    # Step 1: Visit homepage to establish cookies
    print("Visiting homepage...")
    s.get("https://www.naukri.com/", timeout=30)
    time.sleep(2)

    # Step 2: Visit login page to get additional cookies
    print("Visiting login page...")
    s.get("https://www.naukri.com/nlogin/login", timeout=30)
    time.sleep(2)

    # Step 3: Login
    print("Logging in...")
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
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        },
        json={"username": username, "password": password},
        timeout=30
    )

    if r.status_code == 403:
        print("403 on login - printing response for debug:", r.text[:300])
        r.raise_for_status()

    r.raise_for_status()
    print("Login status:", r.status_code)

    # Extract token from cookies or response
    token = s.cookies.get("nauk_at") or s.cookies.get("nkSso")
    if not token:
        # Try extracting from response body
        login_data = r.json()
        token = login_data.get("loginData", {}).get("token", "")
    print("Token obtained:", bool(token))
    time.sleep(1)

    # Step 4: Download PDF from Google Drive
    print("Downloading resume from Google Drive...")
    # Handle Google Drive large file warning redirect
    drive_session = requests.Session()
    drive_session.verify = False
    res = drive_session.get(
        f"https://drive.google.com/uc?export=download&id={file_id}",
        allow_redirects=True,
        timeout=30
    )
    # Handle confirmation page for large files
    if "confirm=" in res.url or b"virus scan warning" in res.content:
        confirm_token = None
        for key, value in res.cookies.items():
            if key.startswith("download_warning"):
                confirm_token = value
                break
        if confirm_token:
            res = drive_session.get(
                f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm_token}",
                timeout=30
            )
    res.raise_for_status()
    print("PDF size:", len(res.content), "bytes")

    # Step 5: Upload resume to Naukri file validation
    print("Uploading resume...")
    upload_resp = s.post(
        "https://filevalidation.naukri.com/file",
        headers={
            "accept": "application/json",
            "appid": "105",
            "origin": "https://www.naukri.com",
            "referer": "https://www.naukri.com/",
            "systemid": "fileupload",
        },
        files={"file": (final_filename, BytesIO(res.content), "application/pdf")},
        data={
            "formKey": form_key,
            "fileName": final_filename,
            "uploadCallback": "true",
            "fileKey": FILE_KEY
        },
        verify=False,
        timeout=30
    )
    upload_resp.raise_for_status()
    print("Upload status:", upload_resp.status_code)
    time.sleep(1)

    # Step 6: Get profile ID from dashboard
    print("Fetching profile ID...")
    d = s.get(
        "https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/dashboard",
        headers={
            "accept": "application/json",
            "appid": "105",
            "clientid": "d3skt0p",
            "systemid": "Naukri",
            "authorization": f"Bearer {token}"
        },
        timeout=30
    )
    d.raise_for_status()
    profile_id = d.json().get("dashBoard", {}).get("profileId")
    print("Profile ID:", profile_id)

    if not profile_id:
        raise ValueError("Could not retrieve profile ID. Check token or session.")

    # Step 7: Update resume
    print("Updating resume on profile...")
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
