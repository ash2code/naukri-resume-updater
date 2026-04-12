# Naukri Resume Auto Update Script

This script automatically updates your Naukri profile resume using a PDF stored on Google Drive.

---

## 🚀 Features

* Login to Naukri
* Download resume from Google Drive
* Upload resume to Naukri
* Update profile automatically
* Can be used with cron jobs

---

## 📦 Setup

### 1. Install dependencies

```bash
pip install requests
```

---

### 2. Configure variables

Open the script and fill:

```python
username = "your_email"
password = "your_password"

file_id = "your_google_drive_file_id"
form_key = "your_form_key"
filename = ""  # optional
```

---

## 📄 How to Upload Resume to Google Drive

1. Go to Google Drive
2. Upload your resume PDF
3. Right click → **Get Link**
4. Make it **Anyone with the link can view**
5. Copy the link

Example link:

```
https://drive.google.com/file/d/1ABCxyz123/view?usp=sharing
```

👉 Your `file_id` is:

```
1ABCxyz123
```

---

## 🔑 How to Get `form_key` (IMPORTANT)

This is required for upload to work.

### Steps:

1. Open Naukri and login
2. Open **DevTools** (F12)
3. Go to **Network tab**
4. Upload resume manually once
5. Look for a request named:

   ```
   filevalidation.naukri.com/file
   ```
6. Click it → go to **Payload / Form Data**
7. Find:

   ```
   formKey: Fxxxxxxxxxxxx
   ```

👉 Copy that value and paste into:

```python
form_key = "Fxxxxxxxxxxxx"
```

---

## ▶️ Usage

Run the script:

```bash
python script.py
```

---

## ⏰ Cron Example

Run every day at 10 AM:

```bash
0 10 * * * python /path/to/script.py
```

---

## ⚠️ Notes

* Resume must be **PDF**
* Google Drive file must be **public**
* Do not share your credentials

---

## ✅ Output

On success:

```json
{
  "success": true,
  "message": "Resume updated successfully"
}
```

---


