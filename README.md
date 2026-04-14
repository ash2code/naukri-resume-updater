# Naukri Resume Auto-Updater

Automatically update your Naukri profile resume every day using GitHub Actions. This keeps your profile active and visible to recruiters.

---

## How It Works

1. Downloads your resume PDF from Google Drive
2. Logs into Naukri using cookies (bypasses OTP)
3. Uploads the resume to your profile
4. Runs daily at 6 AM IST via GitHub Actions

---

## Quick Setup (5 Steps)

### Step 1: Fork This Repository

1. Click the **Fork** button at the top right of this page
2. This creates a copy in your GitHub account

---

### Step 2: Upload Resume to Google Drive

1. Go to [Google Drive](https://drive.google.com)
2. Upload your resume (must be **PDF** format)
3. Right-click the file → **Share** → **General access** → **Anyone with the link**
4. Click **Copy link**

**Example link:**
```
https://drive.google.com/file/d/1ABC123xyz/view?usp=sharing
```

**Your FILE_ID is:** `1ABC123xyz` (the part between `/d/` and `/view`)

---

### Step 3: Get FORM_KEY from Naukri

This is required for resume upload to work.

1. Login to [Naukri.com](https://www.naukri.com)
2. Go to your profile and click **Update Resume**
3. Open **DevTools** (Press `F12`)
4. Go to **Network** tab
5. Upload any resume manually
6. Look for a request to `filevalidation.naukri.com/file`
7. Click it → **Payload** tab → Find `formKey`

**Example:** `formKey: F1a2b3c4d5e6f7`

**Your FORM_KEY is:** `F1a2b3c4d5e6f7`

---

### Step 4: Get NAUKRI_COOKIES

Naukri sends OTP for automated logins. We bypass this using browser cookies.

1. Login to [Naukri.com](https://www.naukri.com) in Chrome (complete OTP if asked)
2. Once logged in, press `F12` to open DevTools
3. Go to **Application** tab → **Cookies** → `https://www.naukri.com`
4. Find and copy these 3 cookies:

| Cookie Name | Example Value |
|-------------|---------------|
| `nauk_at` | `eyJraWQiOiIz...` (very long) |
| `nauk_rt` | `672301de8278...` |
| `nauk_sid` | `672301de8278...` |

5. Format them as one string:

```
nauk_at=YOUR_NAUK_AT_VALUE; nauk_rt=YOUR_NAUK_RT_VALUE; nauk_sid=YOUR_NAUK_SID_VALUE
```

**Quick Method:** Run this in DevTools Console tab:
```javascript
['nauk_at','nauk_rt','nauk_sid'].map(n=>`${n}=${document.cookie.split('; ').find(c=>c.startsWith(n))?.split('=').slice(1).join('=')}`).join('; ')
```

---

### Step 5: Add GitHub Secrets

1. Go to your forked repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add these 3 secrets:

| Secret Name | Value |
|-------------|-------|
| `GOOGLE_DRIVE_FILE_ID` | Your file ID from Step 2 |
| `NAUKRI_FORM_KEY` | Your form key from Step 3 |
| `NAUKRI_COOKIES` | Your cookie string from Step 4 |

---

## Test the Workflow

1. Go to your repository → **Actions** tab
2. Click **Update Naukri Resume** workflow
3. Click **Run workflow** → **Run workflow**
4. Wait for it to complete (green checkmark = success)

---

## Change Schedule

The workflow runs daily at **6 AM IST** by default.

To change the time, edit `.github/workflows/ResumeUpdater.yml`:

```yaml
schedule:
  - cron: '30 0 * * *'  # 6:00 AM IST (00:30 UTC)
```

**Cron format:** `minute hour * * *` (in UTC)

| IST Time | UTC Cron |
|----------|----------|
| 6:00 AM | `30 0 * * *` |
| 7:00 AM | `30 1 * * *` |
| 8:00 AM | `30 2 * * *` |
| 9:00 AM | `30 3 * * *` |

---

## Important Notes

- **Cookies expire in ~30 days** - You need to refresh them monthly by logging into Naukri again and updating the `NAUKRI_COOKIES` secret
- **Resume must be PDF** format
- **Google Drive file must be publicly accessible** (Anyone with the link)
- GitHub Actions may have **5-15 minute delays** during high traffic

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| `Not a valid PDF` | Make sure Google Drive file is public and is a PDF |
| `No auth token` | Cookies expired - refresh them (Step 4) |
| `Profile fetch failed` | Token refresh failed - get new cookies |
| Workflow not running | Check Actions tab is enabled in your fork |

---

## License

MIT - Feel free to use and modify.
