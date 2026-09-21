# ISEED Volume Analysis - Automated Dashboard

**Status:** ✅ Automated refresh via Copilot Cloud Workflow (Daily 6:00 AM)

---

## Quick Summary

This folder contains the **ISEED inventory dashboard** with fully automated refresh pipeline:

- 📧 **Data Source:** DDG/iSEED email folder (Graph API)
- 🔄 **Refresh:** Daily at 6:00 AM (Copilot Cloud Backend)
- 📊 **Dashboard:** `inventory-dashboard.html` (live on GitHub Pages)
- 🔗 **Public Link:** https://nazmi-abd-ghani-intel.github.io/projects/ISEED-Volume-Analysis/inventory-dashboard.html

**No setup required. No credentials to manage. No manual intervention needed.**

---

## How It Works

```
6:00 AM Daily (Automatic - No User Action Needed)
     ↓
Copilot Workflow Agent (Runs on Cloud Backend)
     ├─ Downloads .txt attachments from DDG/iSEED (Graph API)
     ├─ Runs refresh-dashboard-snapshots-only.ps1 (parse & inject)
     ├─ Commits updated HTML to feature branch (git)
     ├─ Opens PR automatically (GitHub CLI)
     └─ GitHub Actions auto-approves & auto-merges
     
Timeline: 6:00-6:05 AM (Download) → 6:05-6:10 AM (Parse & Git) → 
          6:10-6:12 AM (PR Created) → 6:12-6:14 AM (Auto-Merged) →
          6:15 AM (Live on GitHub Pages)

Result: Dashboard updated within ~15 minutes, fully automated
```

### What Actually Happens

**You do NOT need to:**
- Click "Run in the Cloud" (workflow saves automatically)
- Keep your machine ON (runs on Copilot cloud backend)
- Approve PRs (GitHub Actions auto-merges)
- Manually publish (GitHub Pages auto-deploys)

**You only need to:**
- Click "Save" in the Copilot workflow dialog once
- That's it! Workflow runs automatically every day at 6 AM

---

## Files in This Folder

| File | Purpose |
|------|---------|
| `inventory-dashboard.html` | **Published dashboard** (contains DATA + PRODUCT_CONFIG constants) |
| `refresh-dashboard-snapshots-only.ps1` | **Refresh script** (parses existing snapshots, injects into HTML) |
| `refresh-inventory-dashboard.ps1` | Legacy script (not used by workflow; reference only) |
| `README.md` | **Quick reference guide** (you are here) |
| `AUTOMATION-SETUP.md` | **Complete automation documentation** |
| `MANUAL-REFRESH-GUIDE.md` | **How to run script manually** (testing, debugging) |
| `SCRIPT-COMPARISON.md` | **Detailed script comparison** |
| `build-product-config.ps1` | Helper script (generates product config) |
| `Input/Snapshots/` | **Snapshot cache** (downloaded via Graph API) |
| `Input/product-config.csv` | Product mapping definitions |
| `Input/product-config.json` | Generated config (injected into dashboard) |
| `Backups/` | Timestamped dashboard backups |
| `.github/workflows/iseed-auto-merge.yml` | GitHub Actions auto-merge workflow |

---

## Running the Refresh

You have **TWO OPTIONS** to run the dashboard refresh:

### Option 1: Automatic (Recommended) - Copilot Workflow
- ✅ **Runs every day at 6:00 AM automatically**
- ✅ Your machine can be OFF
- ✅ No manual steps needed
- **How to enable:** Click "Save" in Copilot Workflow Editor (one-time setup)

### Option 2: Manual - PowerShell Script
- For testing, debugging, or one-off refreshes
- Requires you to have the latest snapshots in `Input/Snapshots/`
- Command:
  ```powershell
  cd C:\git-repo\nabdghan-git\projects\ISEED-Volume-Analysis
  powershell.exe -ExecutionPolicy Bypass -File refresh-dashboard-snapshots-only.ps1
  ```
- **Outputs:**
  - `Logs/refresh-inventory-dashboard.log` (execution log)
  - `inventory-dashboard.html` (updated dashboard)
  - `Backups/` (previous version backed up)
- **After script runs:** You can manually commit & push if desired:
  ```powershell
  git add inventory-dashboard.html
  git commit -m "chore: manual refresh"
  git push
  ```

---

## Notifications & Status Monitoring

### How to Get Notifications

**GitHub PR Notifications (Email):**
1. Go to https://github.com/nazmi-abd-ghani-intel/projects
2. Click "Watch" → Select "Custom" → Check "Pull requests"
3. You'll receive email when:
   - PR is created (by Copilot Workflow)
   - PR is auto-merged
   - Any comments on PR

**Copilot Workflow Logs:**
- Copilot will show execution summary after each run
- Check for:
  - ✅ "Workflow completed successfully"
  - ⏭️ "No changes needed"
  - ❌ "Workflow aborted at Phase X: [reason]"

**GitHub Actions Log:**
- Go to: https://github.com/nazmi-abd-ghani-intel/projects/actions
- Filter for "ISEED" or "auto-merge"
- See real-time validation status

### What Notifications You'll Receive

| Event | Where | When |
|-------|-------|------|
| PR Created | GitHub Email (if subscribed) | ~6:10 AM |
| Workflow Errors | Copilot Logs | After workflow runs |
| PR Auto-Merged | GitHub Email (if subscribed) | ~6:12 AM |
| Dashboard Updated | GitHub Pages | ~6:15 AM |

### Check Without Waiting for Notifications

**To manually check status:**

1. **Is dashboard updated?**
   - Check live: https://nazmi-abd-ghani-intel.github.io/projects/ISEED-Volume-Analysis/inventory-dashboard.html
   - Or check repo: https://github.com/nazmi-abd-ghani-intel/projects/commits/main/ISEED-Volume-Analysis/

2. **Did PR get created?**
   - Check: https://github.com/nazmi-abd-ghani-intel/projects/pulls
   - Look for "chore: auto-refresh ISEED dashboard"

3. **What was the error?**
   - Check Copilot workflow logs (in Copilot app)
   - Check GitHub Actions: https://github.com/nazmi-abd-ghani-intel/projects/actions

---

## Troubleshooting

| Issue | Check |
|-------|-------|
| "No PR created" | No new attachments or no changes to dashboard (normal if data is stale) |
| "Records < 1000" | Snapshot files missing or too old. Check Input/Snapshots/ folder. |
| "Data drop detected" | New record count < 50% of previous. Manual review before override. |
| "Dashboard not updating" | Check if new emails are arriving in DDG/iSEED folder |
| "GitHub Pages not live" | Verify GitHub Pages is enabled for this repo (Settings → Pages) |

---

## For More Details

**Reading order:**

1. **`README.md`** (you are here) - Quick overview and two options
2. **`MANUAL-REFRESH-GUIDE.md`** - How to run the PowerShell script manually (for testing/debugging)
3. **`AUTOMATION-SETUP.md`** - Complete architecture, safety rules, and troubleshooting
4. **`SCRIPT-COMPARISON.md`** - Detailed comparison between old and new scripts

Or jump directly to what you need:
- **"How do I run it manually?"** → See `MANUAL-REFRESH-GUIDE.md`
- **"How does the automatic workflow work?"** → See `AUTOMATION-SETUP.md`
- **"What's the difference between scripts?"** → See `SCRIPT-COMPARISON.md`

---

## Key Points

✅ **Fully Automated:** Runs on schedule, no manual intervention  
✅ **No Setup:** Uses existing Copilot Graph access, no app registration  
✅ **No Secrets:** No credentials stored (session-level auth only)  
✅ **Cloud-Based:** Runs on Copilot backend (reliable, always available)  
✅ **Safe:** Safety guardrails prevent bad data overwrites  
✅ **Auditable:** All changes tracked in git with commit messages  
✅ **No Machine Required:** Your PC can be OFF, workflow still runs  
✅ **Auto PR & Merge:** Automatically creates and merges pull requests  
✅ **Dashboard Always Updated:** If new snapshots exist, HTML gets updated and published

---

## One-Time Setup

1. Open Copilot Workflow Editor (should open automatically when you review this doc)
2. Click **"Save"** to activate the workflow
3. **Done!** Workflow now runs automatically every day at 6:00 AM

You do NOT need to click "Run in the Cloud" or any other button. Just Save and you're finished.

---

## Questions?

Refer to AUTOMATION-SETUP.md or contact the development team.
