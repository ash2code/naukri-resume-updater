import requests
import json
from io import BytesIO
from datetime import datetime
import os
import random
import sys


# ================== CONFIG (from GitHub Secrets / env vars) ==================
username = os.environ.get("NAUKRI_USERNAME", "")
password = os.environ.get("NAUKRI_PASSWORD", "")
file_id  = os.environ.get("GOOGLE_DRIVE_FILE_ID", "")
form_key = os.environ.get("NAUKRI_FORM_KEY", "")
filename = os.environ.get("RESUME_FILENAME", "")  # Optional override


# ================== UTIL ==================
def generate_file_key(length=13):
    chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "U" + ''.join(random.choice(chars) for _ in range(length))


def download_from_drive(file_id: str) -> bytes:
    """
    Handles Google Drive's virus-scan confirmation page for larger files.
    """
    session = requests.Session()
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    resp = session.get(url, stream=True)
    resp.raise_for_status()

    # Check for confirmation page (large file virus warning)
    content_type = resp.headers.get("Content-Type", "")
    if "text/html" in content_type:
        # Extract confirm token from response
        token = None
        for key, value in resp.cookies.items():
            if key.startswith("download_warning"):
                token = value
                break

        if token:
            confirm_url = f"{url}&confirm={token}"
            resp = session.get(confirm_url, stream=True)
            resp.raise_for_status()
        else:
            raise Exception("Google Drive returned HTML — file may be too large or not publicly shared")

    content = resp.content

    if content[:4] != b'%PDF':
        raise Exception(f"Downloaded content is not a valid PDF (got: {content[:20]})")

    return content


# ================== LOGIN CLIENT ==================
class NaukriLoginClient:
    LOGIN_URL = "https://www.naukri.com/central-login-services/v1/login"
    DASHBOARD_URL = "https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/dashboard"

    BASE_HEADERS = {
        "accept": "application/json",
        "appid": "105",
        "clientid": "d3skt0p",
        "systemid": "jobseeker",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
    }

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._token = None

    def login(self):
        headers = {**self.BASE_HEADERS, "content-type": "application/json", "referer": "https://www.naukri.com/nlogin/login"}
        payload = {"username": self.username, "password": self.password}

        resp = self.session.post(self.LOGIN_URL, headers=headers, json=payload)
        resp.raise_for_status()

        self._token = self.session.cookies.get("nauk_at")
        if not self._token:
            raise Exception("Login succeeded but bearer token (nauk_at) not found in cookies")

        print(f"[✓] Login successful")
        return resp

    def get_bearer_token(self) -> str:
        if not self._token:
            raise Exception("Not logged in — call login() first")
        return self._token

    def get_auth_headers(self) -> dict:
        return {
            **self.BASE_HEADERS,
            "authorization": f"Bearer {self.get_bearer_token()}",
        }

    def fetch_profile_id(self) -> str:
        resp = self.session.get(self.DASHBOARD_URL, headers=self.get_auth_headers())
        resp.raise_for_status()

        data = resp.json()
        profile_id = (
            data.get("dashBoard", {}).get("profileId")
            or data.get("profileId")
        )

        if not profile_id:
            raise Exception(f"Profile ID not found in dashboard response: {json.dumps(data)[:300]}")

        print(f"[✓] Profile ID: {profile_id}")
        return profile_id

    def get_required_cookies(self) -> dict:
        cookies = self.session.cookies.get_dict()
        result = {"test": "naukri.com", "is_login": "1"}
        for key in ["nauk_rt", "nauk_sid", "MYNAUKRI[UNID]"]:
            if cookies.get(key):
                result[key] = cookies[key]
        return result


# ================== UPLOAD ==================
def upload_resume_file(pdf_bytes: bytes, filename: str, form_key: str) -> str:
    """
    Uploads PDF to Naukri file validation endpoint.
    Returns the resolved file key.
    """
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
        files={"file": (filename, BytesIO(pdf_bytes), "application/pdf")},
        data={
            "formKey": form_key,
            "fileName": filename,
            "uploadCallback": "true",
            "fileKey": file_key,
        }
    )
    resp.raise_for_status()

    # Naukri may return a different key — resolve it
    try:
        upload_json = resp.json()
        if file_key not in upload_json:
            file_key = next(iter(upload_json.keys()))
    except Exception:
        pass  # Keep original file_key if parsing fails

    print(f"[✓] Resume uploaded — file key: {file_key}")
    return file_key


# ================== PROFILE UPDATE ==================
def attach_resume_to_profile(client: NaukriLoginClient, profile_id: str, form_key: str, file_key: str):
    url = f"https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/profiles/{profile_id}/advResume"

    payload = {
        "textCV": {
            "formKey": form_key,
            "fileKey": file_key,
            "textCvContent": None
        }
    }

    resp = client.session.post(
        url,
        headers={
            **client.get_auth_headers(),
            "content-type": "application/json",
            "origin": "https://www.naukri.com",
            "referer": "https://www.naukri.com/",
            "x-http-method-override": "PUT",
        },
        cookies=client.get_required_cookies(),
        data=json.dumps(payload)
    )
    resp.raise_for_status()
    print(f"[✓] Resume attached to profile successfully")


# ================== MAIN ==================
def update_resume() -> dict:
    # ---- Validate config ----
    missing = [k for k, v in {"NAUKRI_USERNAME": username, "NAUKRI_PASSWORD": password,
                               "GOOGLE_DRIVE_FILE_ID": file_id, "NAUKRI_FORM_KEY": form_key}.items() if not v]
    if missing:
        return {"success": False, "error": f"Missing env vars: {', '.join(missing)}"}

    today = datetime.now()
    final_filename = filename or f"resume_{today.strftime('%d_%B_%Y').lower()}.pdf"
    print(f"[→] Resume filename: {final_filename}")

    # ---- Login ----
    client = NaukriLoginClient(username, password)
    try:
        client.login()
    except Exception as e:
        return {"success": False, "error": f"Login failed: {e}"}

    # ---- Download from Google Drive ----
    print(f"[→] Downloading resume from Google Drive...")
    try:
        pdf_bytes = download_from_drive(file_id)
        print(f"[✓] Downloaded {len(pdf_bytes):,} bytes")
    except Exception as e:
        return {"success": False, "error": f"Download failed: {e}"}

    # ---- Upload to Naukri ----
    print(f"[→] Uploading to Naukri...")
    try:
        file_key = upload_resume_file(pdf_bytes, final_filename, form_key)
    except Exception as e:
        return {"success": False, "error": f"Upload failed: {e}"}

    # ---- Fetch profile ID ----
    try:
        profile_id = client.fetch_profile_id()
    except Exception as e:
        return {"success": False, "error": f"Profile fetch failed: {e}"}

    # ---- Attach resume to profile ----
    try:
        attach_resume_to_profile(client, profile_id, form_key, file_key)
    except Exception as e:
        return {"success": False, "error": f"Profile update failed: {e}"}

    return {
        "success": True,
        "file_key": file_key,
        "filename": final_filename,
        "message": "Resume updated successfully on Naukri"
    }


# ================== ENTRY POINT ==================
if __name__ == "__main__":
    print("=" * 50)
    print("Naukri Resume Auto-Updater")
    print("=" * 50)

    result = update_resume()

    print("\n" + "=" * 50)
    if result["success"]:
        print(f"✅ SUCCESS: {result['message']}")
        print(f"   File: {result['filename']}")
        print(f"   Key:  {result['file_key']}")
    else:
        print(f"❌ FAILED: {result['error']}")
        sys.exit(1)  # Non-zero exit so GitHub Actions marks the job as failed
