import requests
import json
import urllib3
from io import BytesIO
from datetime import datetime
import os
import random
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

username = os.environ.get("NAUKRI_USERNAME", "")
password = os.environ.get("NAUKRI_PASSWORD", "")
file_id  = os.environ.get("GOOGLE_DRIVE_FILE_ID", "")
form_key = os.environ.get("NAUKRI_FORM_KEY", "")
filename = os.environ.get("RESUME_FILENAME", "")


def generate_file_key():
    chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "U" + ''.join(random.choice(chars) for _ in range(13))


def download_from_drive(fid):
    session = requests.Session()
    session.verify = False
    url = f"https://drive.google.com/uc?export=download&id={fid}"
    resp = session.get(url, stream=True)
    resp.raise_for_status()

    if "text/html" in resp.headers.get("Content-Type", ""):
        token = next((v for k, v in resp.cookies.items() if k.startswith("download_warning")), None)
        if not token:
            raise Exception("Google Drive returned HTML page - file may not be publicly shared")
        resp = session.get(f"{url}&confirm={token}", stream=True)
        resp.raise_for_status()

    if resp.content[:4] != b'%PDF':
        raise Exception("Downloaded content is not a valid PDF")

    return resp.content


class NaukriClient:
    LOGIN_URL = "https://www.naukri.com/central-login-services/v1/login"
    DASHBOARD_URL = "https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/dashboard"

    BASE_HEADERS = {
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9",
        "appid": "105",
        "appname": "naukri",
        "clientid": "d3skt0p",
        "gid": "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
        "systemid": "jobseeker",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
    }

    def __init__(self, uname, pwd):
        self.username = uname
        self.password = pwd
        self.session = requests.Session()
        self.session.verify = False
        self._token = None

    def login(self):
        resp = self.session.post(
            self.LOGIN_URL,
            headers={
                **self.BASE_HEADERS,
                "content-type": "application/json",
                "origin": "https://www.naukri.com",
                "referer": "https://www.naukri.com/nlogin/login",
            },
            json={
                "username": self.username,
                "password": self.password,
                "usertype": "1",
                "token": "",
            }
        )

        if resp.status_code != 200:
            print(f"[FAIL] Login {resp.status_code}: {resp.text[:500]}")

        resp.raise_for_status()

        self._token = self.session.cookies.get("nauk_at")
        if not self._token:
            try:
                body = resp.json()
                self._token = body.get("loginData", {}).get("token") or body.get("token")
            except Exception:
                pass

        if not self._token:
            raise Exception("Bearer token not found after login")

        print(f"[OK] Login successful, token: {self._token[:20]}...")

    def auth_headers(self):
        return {**self.BASE_HEADERS, "authorization": f"Bearer {self._token}"}

    def required_cookies(self):
        cookies = self.session.cookies.get_dict()
        result = {"test": "naukri.com", "is_login": "1"}
        for key in ["nauk_rt", "nauk_sid", "MYNAUKRI[UNID]"]:
            if cookies.get(key):
                result[key] = cookies[key]
        return result

    def fetch_profile_id(self):
        resp = self.session.get(self.DASHBOARD_URL, headers=self.auth_headers())

        print(f"[->] Dashboard status: {resp.status_code}")
        print(f"[->] Dashboard body: {resp.text[:500]}")

        resp.raise_for_status()

        if not resp.text.strip():
            raise Exception("Dashboard returned empty response body")

        data = resp.json()
        profile_id = data.get("dashBoard", {}).get("profileId") or data.get("profileId")

        if not profile_id:
            raise Exception(f"Profile ID not found in: {json.dumps(data)[:300]}")

        print(f"[OK] Profile ID: {profile_id}")
        return profile_id

    def upload_resume(self, pdf_bytes, fname, fkey):
        file_key = generate_file_key()
        resp = requests.post(
            "https://filevalidation.naukri.com/file",
            headers={
                "accept": "application/json",
                "appid": "105",
                "origin": "https://www.naukri.com",
                "referer": "https://www.naukri.com/",
                "systemid": "fileupload",
                "user-agent": "Mozilla/5.0",
            },
            files={"file": (fname, BytesIO(pdf_bytes), "application/pdf")},
            data={
                "formKey": fkey,
                "fileName": fname,
                "uploadCallback": "true",
                "fileKey": file_key,
            },
            verify=False
        )
        resp.raise_for_status()

        try:
            upload_json = resp.json()
            if file_key not in upload_json:
                file_key = next(iter(upload_json.keys()))
        except Exception:
            pass

        print(f"[OK] Uploaded, file key: {file_key}")
        return file_key

    def attach_resume(self, profile_id, fkey, file_key):
        resp = self.session.post(
            f"https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/profiles/{profile_id}/advResume",
            headers={
                **self.auth_headers(),
                "content-type": "application/json",
                "origin": "https://www.naukri.com",
                "referer": "https://www.naukri.com/",
                "x-http-method-override": "PUT",
            },
            cookies=self.required_cookies(),
            data=json.dumps({
                "textCV": {
                    "formKey": fkey,
                    "fileKey": file_key,
                    "textCvContent": None
                }
            })
        )
        resp.raise_for_status()
        print("[OK] Resume attached to profile")


def update_resume():
    missing = [k for k, v in {
        "NAUKRI_USERNAME": username,
        "NAUKRI_PASSWORD": password,
        "GOOGLE_DRIVE_FILE_ID": file_id,
        "NAUKRI_FORM_KEY": form_key
    }.items() if not v]

    if missing:
        return {"success": False, "error": f"Missing env vars: {', '.join(missing)}"}

    final_filename = filename or f"resume_{datetime.now().strftime('%d_%B_%Y').lower()}.pdf"
    print(f"[->] Filename: {final_filename}")

    client = NaukriClient(username, password)

    try:
        client.login()
    except Exception as e:
        return {"success": False, "error": f"Login failed: {e}"}

    try:
        print("[->] Downloading from Google Drive...")
        pdf_bytes = download_from_drive(file_id)
        print(f"[OK] Downloaded {len(pdf_bytes):,} bytes")
    except Exception as e:
        return {"success": False, "error": f"Download failed: {e}"}

    try:
        file_key = client.upload_resume(pdf_bytes, final_filename, form_key)
    except Exception as e:
        return {"success": False, "error": f"Upload failed: {e}"}

    try:
        profile_id = client.fetch_profile_id()
    except Exception as e:
        return {"success": False, "error": f"Profile fetch failed: {e}"}

    try:
        client.attach_resume(profile_id, form_key, file_key)
    except Exception as e:
        return {"success": False, "error": f"Profile update failed: {e}"}

    return {"success": True, "filename": final_filename, "file_key": file_key}


if __name__ == "__main__":
    print("=" * 50)
    result = update_resume()
    print("=" * 50)
    if result["success"]:
        print(f"SUCCESS: Resume updated: {result['filename']}")
    else:
        print(f"FAILED: {result['error']}")
        sys.exit(1)
