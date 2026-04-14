import requests
import urllib3
from io import BytesIO
from datetime import datetime
import os
import random
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

COOKIES = os.environ.get("NAUKRI_COOKIES", "")
FILE_ID = os.environ.get("GOOGLE_DRIVE_FILE_ID", "")
FORM_KEY = os.environ.get("NAUKRI_FORM_KEY", "")

HEADERS = {
    "accept": "application/json",
    "appid": "105",
    "clientid": "d3skt0p",
    "systemid": "jobseeker",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
}


def download_pdf(file_id):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    resp = requests.get(url, verify=False)
    resp.raise_for_status()
    if resp.content[:4] != b'%PDF':
        raise Exception("Not a valid PDF or file not publicly shared")
    return resp.content


def parse_cookies(cookie_str):
    cookies = {}
    for pair in cookie_str.split(';'):
        if '=' in pair:
            k, v = pair.strip().split('=', 1)
            cookies[k.strip()] = v.strip()
    return cookies


def refresh_token(session, refresh_token_val):
    resp = session.post(
        "https://www.naukri.com/central-login-services/v1/login/token/refresh",
        headers={**HEADERS, "content-type": "application/json"},
        json={"refreshToken": refresh_token_val},
        verify=False
    )
    if resp.status_code == 200:
        return session.cookies.get("nauk_at")
    return None


def get_profile_id(session, token):
    resp = session.get(
        "https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/dashboard",
        headers={**HEADERS, "authorization": f"Bearer {token}"},
        verify=False
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("dashBoard", {}).get("profileId") or data.get("profileId")


def upload_file(pdf_bytes, filename, form_key):
    file_key = "U" + ''.join(random.choice("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(13))
    resp = requests.post(
        "https://filevalidation.naukri.com/file",
        headers={"appid": "105", "systemid": "fileupload"},
        files={"file": (filename, BytesIO(pdf_bytes), "application/pdf")},
        data={"formKey": form_key, "fileName": filename, "fileKey": file_key},
        verify=False
    )
    resp.raise_for_status()
    return file_key


def attach_to_profile(session, token, profile_id, form_key, file_key):
    resp = session.post(
        f"https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/profiles/{profile_id}/advResume",
        headers={**HEADERS, "authorization": f"Bearer {token}", "content-type": "application/json", "x-http-method-override": "PUT"},
        json={"textCV": {"formKey": form_key, "fileKey": file_key, "textCvContent": None}},
        verify=False
    )
    resp.raise_for_status()


def main():
    if not all([COOKIES, FILE_ID, FORM_KEY]):
        print("Missing: NAUKRI_COOKIES, GOOGLE_DRIVE_FILE_ID, or NAUKRI_FORM_KEY")
        sys.exit(1)

    session = requests.Session()
    cookies = parse_cookies(COOKIES)
    for k, v in cookies.items():
        session.cookies.set(k, v, domain='.naukri.com')

    token = cookies.get("nauk_at")
    if cookies.get("nauk_rt"):
        new_token = refresh_token(session, cookies["nauk_rt"])
        if new_token:
            token = new_token
            print("[OK] Token refreshed")

    if not token:
        print("No auth token available")
        sys.exit(1)

    print("[OK] Authenticated")

    pdf = download_pdf(FILE_ID)
    print(f"[OK] Downloaded PDF ({len(pdf):,} bytes)")

    filename = f"resume_{datetime.now().strftime('%d_%b_%Y').lower()}.pdf"
    file_key = upload_file(pdf, filename, FORM_KEY)
    print(f"[OK] Uploaded: {filename}")

    profile_id = get_profile_id(session, token)
    print(f"[OK] Profile ID: {profile_id}")

    attach_to_profile(session, token, profile_id, FORM_KEY, file_key)
    print("[OK] Resume updated!")


if __name__ == "__main__":
    main()
