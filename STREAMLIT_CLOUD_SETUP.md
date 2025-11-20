# Streamlit Cloud Setup Guide

This guide walks you through setting up sensitive configuration information in Streamlit Cloud.

## Method 1: Using Streamlit Secrets (Recommended)

Streamlit Cloud provides a secure way to store sensitive information using **Secrets**.

### Step 1: Access Your Streamlit Cloud App

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Select your app from the dashboard

### Step 2: Open App Settings

1. Click on the **"⋮" (three dots)** menu next to your app
2. Select **"Settings"** from the dropdown menu

### Step 3: Navigate to Secrets

1. In the Settings page, look for the **"Secrets"** section in the left sidebar
2. Click on **"Secrets"**

### Step 4: Add Your Configuration Values

Streamlit Secrets uses a TOML format. Add your configuration values like this:

```toml
# Streamlit Secrets (.streamlit/secrets.toml format)

# Google Earth Engine Configuration
[gee]
project_name = "your-gee-project-id"
export_folder = "your-google-drive-folder-id"

# Google Drive Configuration
[drive]
raw_data_folder_id = "your-raw-data-folder-id"
```

**Note:** Replace the placeholder values with your actual values. Never commit actual values to Git.

### Step 5: Save and Redeploy

1. Click **"Save"** at the bottom of the Secrets editor
2. Your app will automatically redeploy with the new secrets
3. The secrets will be available as `st.secrets["gee"]["project_name"]`, etc.

---

## Method 2: Environment Variables (Alternative)

If you prefer using environment variables, you can set them in Streamlit Cloud:

### Step 1: Access App Settings

Same as Method 1, Steps 1-2

### Step 2: Set Environment Variables

1. In Settings, look for **"Environment variables"** section
2. Add variables with the `RC_` prefix:

| Variable Name | Value |
|--------------|-------|
| `RC_GEE__PROJECT_NAME` | `your-gee-project-id` |
| `RC_GEE__EXPORT_FOLDER` | `your-google-drive-folder-id` |
| `RC_DRIVE__RAW_DATA_FOLDER_ID` | `your-raw-data-folder-id` |

**Note:** Use double underscore `__` for nested keys:
- `RC_GEE__PROJECT_NAME` → `gee.project_name`
- `RC_GEE__EXPORT_FOLDER` → `gee.export_folder`
- `RC_DRIVE__RAW_DATA_FOLDER_ID` → `drive.raw_data_folder_id`

### Step 3: Save and Redeploy

1. Click **"Save"**
2. Your app will redeploy with the new environment variables

---

## Method 3: Using config.example.yaml (Temporary/Development)

If you just want to test the app quickly:

1. The app will automatically use `configs/config.example.yaml` if no other config is found
2. **Warning:** This contains placeholder values and may cause errors
3. For production, use Method 1 or 2 above

---

## How the App Loads Configuration

The app uses a **fallback system** in this order:

1. **`configs/config.yaml`** (local file - won't exist in Streamlit Cloud)
2. **Environment variables** (Method 2 - if you set them)
3. **Streamlit Secrets** (Method 1 - if you set them)
4. **`configs/config.example.yaml`** (template with placeholders - last resort)

The configuration loader automatically:
- Loads `.env` files if present (using python-dotenv)
- Merges environment variables with file configs
- Provides helpful error messages if nothing is found

---

## Complete Example: Setting Up All Required Values

### Option A: Using Streamlit Secrets (Recommended)

In Streamlit Cloud Secrets editor, paste:

```toml
# Google Earth Engine Configuration
[gee]
project_name = "your-actual-gee-project-id"
export_folder = "your-actual-google-drive-folder-id"

# Google Drive API Configuration  
[drive]
raw_data_folder_id = "your-actual-raw-data-folder-id"

# Optional: If you have Google Drive credentials as JSON
[google_drive]
credentials = '''
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "...",
  "client_id": "...",
  "auth_uri": "...",
  "token_uri": "...",
  "auth_provider_x509_cert_url": "...",
  "client_x509_cert_url": "..."
}
'''
```

### Option B: Using Environment Variables

In Streamlit Cloud Environment Variables:

```
RC_GEE__PROJECT_NAME=your-actual-gee-project-id
RC_GEE__EXPORT_FOLDER=your-actual-google-drive-folder-id
RC_DRIVE__RAW_DATA_FOLDER_ID=your-actual-raw-data-folder-id
```

---

## Verifying Your Setup

After saving secrets/environment variables:

1. **Check the app logs** in Streamlit Cloud:
   - Go to your app dashboard
   - Click on **"Manage app"** → **"Logs"**
   - Look for any configuration errors

2. **Test the app**:
   - The app should load without configuration errors
   - If using `config.example.yaml`, you'll see a warning message
   - Maps should display correctly (if data is available)

---

## Troubleshooting

### Error: "Configuration file not found"

**Solution:** The app is trying to load `config.yaml` which doesn't exist. Set up Streamlit Secrets (Method 1) or Environment Variables (Method 2).

### Error: "WARNING: Using example configuration"

**Solution:** This means the app is using placeholder values. Set up Streamlit Secrets or Environment Variables with your actual values.

### Maps not displaying

**Possible causes:**
1. Configuration values are placeholders (check logs)
2. Data files are missing (GeoTIFF files need to be in the repository or accessible)
3. Google Drive API not configured (if using automatic downloads)

### Google Drive API errors

**Solution:** Ensure you've set up Google Drive API credentials:
1. Create OAuth 2.0 credentials in Google Cloud Console
2. Add credentials to Streamlit Secrets or as environment variables
3. See `SETUP_GUIDE.md` for detailed Google Drive API setup

---

## Security Best Practices

**DO:**
- Use Streamlit Secrets for sensitive information
- Keep `config.yaml` out of Git (already in `.gitignore`)
- Use environment variables in CI/CD pipelines
- Rotate credentials periodically
- Only use placeholder values in documentation

**DON'T:**
- Commit `config.yaml` to Git
- Share secrets in public repositories
- Hardcode credentials in your code
- Use placeholder values in production
- Include actual sensitive values in any files committed to Git

---

## Quick Reference

| Configuration Method | Best For | Security Level |
|---------------------|----------|----------------|
| Streamlit Secrets | Production apps | High |
| Environment Variables | CI/CD, automation | High |
| config.yaml (local) | Local development | Medium |
| config.example.yaml | Testing only | Low (placeholders) |

---

## Need Help?

- Check the main `README.md` for general setup instructions
- See `SETUP_GUIDE.md` for detailed Google Drive API setup
- Review `TROUBLESHOOTING.md` for common issues

