# ISEED Volume Analysis - Automated Dashboard

**Status:** ✅ Automated refresh via Copilot Cloud Workflow (Daily 6:00 AM)

---

## Quick Summary

This folder contains the **ISEED inventory dashboard** with fully automated refresh pipeline:

- 📧 **Data Source:** DDG/iSEED email folder (Graph API)
- 🔄 **Refresh:** GitHub Actions on every new snapshot + daily 06:00 MYT (see `AUTOMATION-SETUP.md`)
- 📊 **Dashboard:** `inventory-dashboard.html` (live on GitHub Pages)
- 🔗 **Public Link:** https://nazmi-abd-ghani-intel.github.io/projects/ISEED-Volume-Analysis/inventory-dashboard.html

**No setup required. No credentials to manage. No manual intervention needed.**

---

## How It Works

```
New iSEED mail in DDG/iSEED
     ↓
Power Automate → SharePoint KeysSnapshot folder (cloud)
     ↓ OneDrive sync
VM Task Scheduler: sync-snapshots.ps1 commits new .txt to Input/Snapshots/ on main
     ↓
GitHub Actions: iseed-refresh.yml (cloud runner; also daily 22:00 UTC / 06:00 MYT)
     ├─ Runs refresh-dashboard-snapshots-fast.ps1 (parse & inject)
     ├─ Encoding integrity check (refuses corrupted HTML)
     ├─ Skips commit when data unchanged
     └─ Commits inventory-dashboard.html to main → GitHub Pages redeploys
```

### What Actually Happens

- The dashboard HTML is **only** written by the Actions job — never by a person or an agent.
- The VM only needs to be signed in with OneDrive running — no Outlook or Copilot app required.
- Manual re-run: Actions tab → *ISEED Dashboard Refresh* → *Run workflow*.

---

## Files in This Folder

| File | Purpose |
|------|---------|
| `inventory-dashboard.html` | **Published dashboard** (contains DATA + PRODUCT_CONFIG constants) |
| `refresh-dashboard-snapshots-fast.ps1` | **Refresh script** (parses existing snapshots, injects into HTML) |
| `sync-snapshots.ps1` | **Feeder script** (SharePoint/OneDrive folder → git push; run by Task Scheduler) |
| `refresh-inventory-dashboard.ps1` | Legacy script (not used by workflow; reference only) |
| `README.md` | **Quick reference guide** (you are here) |
| `AUTOMATION-SETUP.md` | **Complete automation documentation** |
| `build-product-config.ps1` | Helper script (generates product config) |
| `Input/Snapshots/` | **Snapshot files** (git-tracked; committed by the feeder) |
| `Input/product-config.csv` | Product mapping definitions |
| `Input/product-config.json` | Generated config (injected into dashboard) |
| `Backups/` | Timestamped dashboard backups |
| `.github/workflows/iseed-refresh.yml` | **GitHub Actions refresh workflow** (builds & commits the dashboard) |
| `.github/workflows/iseed-auto-merge.yml` | Legacy PR auto-merge workflow |

---

## Running the Refresh

You have **THREE WAYS** to refresh the dashboard:

### Option 1: Automatic (Recommended) - GitHub Actions + Task Scheduler
- ✅ Runs on every new snapshot commit (Hop 2 push) and daily at 06:00 MYT (Hop 3 cron)
- ✅ Cloud-based (your machine can be off)
- ✅ Only commits when the data actually changed
- **Details:** See `AUTOMATION-SETUP.md` → Architecture & Hops

### Option 2: Manual - GitHub Actions (on-demand)
- Click Actions tab → **ISEED Dashboard Refresh** → **Run workflow** → tick **Commit the refreshed dashboard**
- Rebuilds from existing snapshots, commits if data changed
- **Speed:** ~2 min
- **Use case:** Test a config change, force immediate refresh without waiting for 06:00

### Option 3: Manual - PowerShell Scripts (two flavors)

**A. Fast local rebuild (no download):**
```powershell
cd ISEED-Volume-Analysis
powershell -NoProfile -ExecutionPolicy Bypass -File refresh-dashboard-snapshots-fast.ps1
```
- Parses existing snapshots, rebuilds HTML locally
- **Does NOT commit** — you decide afterward
- **Speed:** ~30 sec
- **Use case:** Debug, test changes locally

**B. End-to-end (download + rebuild + commit):**
```powershell
cd ISEED-Volume-Analysis
powershell -NoProfile -ExecutionPolicy Bypass -File refresh-inventory-dashboard.ps1 -Method Outlook -Unattended
```
- Downloads fresh attachments from Outlook
- Parses, rebuilds, **auto-commits and pushes** to `main`
- **Speed:** ~1–2 min
- **Use case:** Force immediate refresh, or if Hop 1 (Power Automate) is broken

**Details:** See `AUTOMATION-SETUP.md` → Manual refresh

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

**Complete documentation:** `AUTOMATION-SETUP.md` (single source of truth for setup, operation, troubleshooting, and daily timeline).

Or jump directly to what you need:
- **"How do I run it manually?"** → `AUTOMATION-SETUP.md` → Manual refresh section
- **"How does the automatic workflow work?"** → `AUTOMATION-SETUP.md` → Hop 1/2/3 sections
- **"What's running on my VM?"** → `AUTOMATION-SETUP.md` → Hop 2 section
- **"My Task Scheduler failed. What now?"** → `AUTOMATION-SETUP.md` → Troubleshooting section

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

Nothing to do on your end. Hops 2 & 3 (Task Scheduler + Actions) are already registered and live. Hop 1 (Power Automate flow) awaits your build — see `AUTOMATION-SETUP.md` → Hop 1.

---

## For Future Maintainers

| Role | Reference |
|------|-----------|
| **Build or rebuild Hop 1** (Power Automate flow) | `AUTOMATION-SETUP.md` → Hop 1 section (step-by-step build) |
| **Modify refresh logic** (parsing, injection, encoding) | Edit `refresh-dashboard-snapshots-fast.ps1`; test with manual run; Hop 3 will use the updated script |
| **Change the daily trigger time** | Task Scheduler: `Get-ScheduledTask 'ISEED Snapshot Sync'`; modify the trigger; or re-register using the snippet in `AUTOMATION-SETUP.md` → Hop 2 |
| **Add another daily run time** | Example: to publish same-day, add 14:00 trigger to Task Scheduler (see Hop 2 setup) |
| **Skip a scheduled run** | Disable Task Scheduler trigger, or set the next 06:00 to "Run whether user logged in or not" (trades OneDrive sync reliability for unattended run) |
| **Troubleshoot Hop 1** | `make.powerautomate.com` → My flows → 28-day run history; flow often fails on SharePoint folder path or blank file name |
| **Troubleshoot Hop 2** | `Get-ScheduledTaskInfo 'ISEED Snapshot Sync'`; `Get-Content Logs/sync-snapshots.log -Tail 50`; `Start-ScheduledTask` for manual run |
| **Troubleshoot Hop 3** | GitHub Actions tab → *ISEED Dashboard Refresh* → latest run; check "DATA changed" output and any encode/parse errors |
| **Inspect what committed** | `git log --oneline` (data/iseed or chore/iseed commits); `git show <hash>` to see which .txt files were added or what HTML changed |

---

## One-Time Setup

1. **`README.md`** (you are here) - Quick overview and file table
2. **`AUTOMATION-SETUP.md`** - Complete reference: Hops 1/2/3, daily timeline, manual refresh, troubleshooting

---

## Questions?

Refer to AUTOMATION-SETUP.md or contact the development team.
