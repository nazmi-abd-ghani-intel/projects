# ISEED Dashboard Auto-Refresh Setup

## Overview

This document captures the complete automated ISEED dashboard refresh pipeline deployed on **2026-09-17**.

The system automatically pulls the latest inventory snapshots from Outlook email, updates the ISEED dashboard HTML, and publishes it globally via GitHub Pages—**no manual intervention required**.

---

## Architecture

```
Windows Task Scheduler (Daily 6:00 AM)
         ↓
refresh-iseed-and-push.ps1
   ├─ Runs: refresh-inventory-dashboard.ps1
   │   └─ Connects to Outlook
   │   └─ Downloads latest snapshot attachments
   │   └─ Parses inventory data
   │   └─ Updates dashboard HTML
   ├─ Creates feature branch: iseed/refresh-YYYYMMDD-HHMMSS
   ├─ Commits updated dashboard
   └─ Creates PR via GitHub CLI
         ↓
GitHub Actions Workflow: iseed-auto-merge.yml
   ├─ Validates dashboard HTML
   │   └─ Checks for DATA marker
   │   └─ Checks for PRODUCT_CONFIG marker
   ├─ Auto-approves PR
   └─ Auto-merges to main (squash commit)
         ↓
GitHub Pages (Deployment)
   └─ Publishes to: https://nazmi-abd-ghani-intel.github.io/projects/ISEED-Volume-Analysis/inventory-dashboard.html

```

---

## Deployed Components

### 1. Refresh Script
**File:** `C:\Scripts\refresh-iseed-and-push.ps1`

**Purpose:**
- Orchestrates the entire refresh pipeline
- Calls the native ISEED refresh script
- Creates PR with updated dashboard
- Supports auto-merge workflow

**Invoked By:** Windows Task Scheduler (daily at 6 AM)

**Process:**
1. Navigates to `ISEED-Volume-Analysis` folder
2. Runs `refresh-inventory-dashboard.ps1 -Method Outlook`
3. Detects changes in dashboard HTML
4. Creates feature branch `iseed/refresh-<timestamp>`
5. Commits updated HTML with co-author trailer
6. Pushes feature branch
7. Creates PR using GitHub CLI
8. Enables auto-merge (squash merge strategy)

---

### 2. GitHub Actions Workflow
**File:** `.github/workflows/iseed-auto-merge.yml`

**Purpose:**
- Automatically validates dashboard updates
- Auto-approves refresh PRs
- Auto-merges to main branch
- Maintains audit trail

**Triggers:**
- Pull request events targeting `main`
- Filters: Changes to `ISEED-Volume-Analysis/inventory-dashboard.html`

**Validations:**
- Checks file exists
- Verifies `const DATA=` marker present
- Verifies `const PRODUCT_CONFIG=` marker present

**Actions:**
- Auto-approve PR
- Auto-merge with squash strategy
- Automatically delete feature branch

---

### 3. Windows Scheduled Task
**Name:** `ISEED-Dashboard-Refresh`

**Schedule:** Daily at 6:00 AM

**Command:**
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Scripts\refresh-iseed-and-push.ps1
```

**Status:** Enabled

**Verify Status:**
```powershell
schtasks /query /tn "ISEED-Dashboard-Refresh" /v
```

---

### 4. GitHub Pages
**URL:** `https://nazmi-abd-ghani-intel.github.io/projects/ISEED-Volume-Analysis/inventory-dashboard.html`

**Source:** Main branch, root folder (/)

**Setup:** Repository Settings → Pages → Deploy from main branch

---

## How It Works

### Daily Refresh Flow (6:00 AM)

1. **[6:00 AM]** Windows Task Scheduler triggers
2. **[Local Machine]** PowerShell script runs
   - Connects to Outlook (iSEED folder)
   - Downloads any new snapshot attachments
   - Parses inventory data
   - Rebuilds product configuration
   - Updates `inventory-dashboard.html`
3. **[Git]** Script creates feature branch and PR
4. **[GitHub]** Actions workflow validates and merges automatically
5. **[Pages]** Updated dashboard is live within 1 minute

### Data Flow

```
Outlook Email (iSEED folder)
   ↓ [Attachment: *.txt]
Input/Snapshots/*.txt (parsed)
   ↓ [Normalized records]
inventory-dashboard.html (injected DATA constant)
   ↓ [PR + Auto-merge]
GitHub main branch
   ↓ [Pages deploys]
https://nazmi-abd-ghani-intel.github.io/projects/ISEED-Volume-Analysis/inventory-dashboard.html (Live)
```

---

## File Locations

| Component | Path | Purpose |
|-----------|------|---------|
| Refresh Script | `C:\Scripts\refresh-iseed-and-push.ps1` | Local automation orchestrator |
| Workflow | `.github/workflows/iseed-auto-merge.yml` | Auto-validation and merge |
| Dashboard | `ISEED-Volume-Analysis/inventory-dashboard.html` | Published dashboard |
| Source Snapshots | `ISEED-Volume-Analysis/Input/Snapshots/*.txt` | Outlook attachment storage |
| Product Config | `ISEED-Volume-Analysis/Input/product-config.csv` | Mapping reference |
| Product Config (Generated) | `ISEED-Volume-Analysis/Input/product-config.json` | Injected into dashboard |
| Backups | `ISEED-Volume-Analysis/Backups/` | Timestamped dashboard backups |

---

## Dashboard Access

**Public Share Link:**
```
https://nazmi-abd-ghani-intel.github.io/projects/ISEED-Volume-Analysis/inventory-dashboard.html
```

**Repository Link:**
```
https://github.com/nazmi-abd-ghani-intel/projects/blob/main/ISEED-Volume-Analysis/inventory-dashboard.html
```

---

## Manual Testing

To test the pipeline without waiting for the scheduled time:

```powershell
C:\Scripts\refresh-iseed-and-push.ps1
```

This will:
1. Run the refresh immediately
2. Create a test PR
3. Show auto-merge in action
4. Demonstrate the entire workflow

---

## Troubleshooting

### PR Not Created
- **Check:** GitHub CLI authentication: `gh auth status`
- **Check:** Network connectivity to GitHub
- **Check:** No changes detected (snapshots haven't changed)

### Dashboard Not Updating
- **Check:** Outlook folder still exists: `\\nazmi.abd.ghani@intel.com\DDG\iSEED`
- **Check:** New snapshot emails are arriving in the folder
- **Check:** Refresh script ran (check Windows Event Viewer for scheduled task logs)

### Pages Not Live
- **Check:** GitHub Pages enabled in repo settings
- **Check:** Source set to `main` branch, `/` folder
- **Check:** Workflow completed successfully (check Actions tab)

### Validation Failures
- **Check:** Dashboard contains `const DATA=` marker
- **Check:** Dashboard contains `const PRODUCT_CONFIG=` marker
- **Check:** HTML file is not corrupted

---

## Maintenance

### Disable Auto-Refresh (Temporary)
```powershell
schtasks /change /tn "ISEED-Dashboard-Refresh" /disable
```

### Re-enable Auto-Refresh
```powershell
schtasks /change /tn "ISEED-Dashboard-Refresh" /enable
```

### Delete Scheduled Task (Permanent)
```powershell
schtasks /delete /tn "ISEED-Dashboard-Refresh" /f
```

### Change Refresh Time (e.g., to 5:00 AM)
```powershell
schtasks /change /tn "ISEED-Dashboard-Refresh" /st 05:00
```

---

## Dependencies

| Component | Version | Required |
|-----------|---------|----------|
| PowerShell | 5.0+ | Yes |
| GitHub CLI (gh) | Latest | Yes |
| Outlook Desktop | Installed | Yes (for Outlook method) |
| Git | 2.0+ | Yes |

---

## Audit Trail

All refreshes create a commit in the repository with:
- Timestamp of refresh
- PR number (squash-merged)
- Automated commit message
- Co-author trailer (Copilot App)

Example commit message:
```
chore: auto-refresh ISEED dashboard [2026-09-18 06:00:00]

Automated by cron job. Latest Outlook snapshot data.

Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>
```

---

## Deployment Date

**Date:** 2026-09-17
**Time:** 20:45 UTC-7
**Deployed By:** Copilot CLI ISEED Agent
**First Scheduled Run:** 2026-09-18 06:00:00 AM

---

## Questions?

Refer to the agent instructions or review the workflow YAML for implementation details.

