# ISEED Dashboard Auto-Refresh Setup

## Overview

This document describes the automated ISEED dashboard refresh pipeline deployed on **2026-09-21** (updated 2026-09-21).

The system automatically pulls the latest inventory snapshots from Outlook email, updates the ISEED dashboard HTML, and publishes it globally via GitHub Pages—**no manual intervention, no Azure setup, no local scheduling required**.

---

## Architecture (Copilot Workflow)

```
Copilot Cloud Backend (Daily 6:00 AM)
         ↓
Copilot Workflow Agent (Autopilot Mode)
   ├─ Phase 1: Graph API Email Collection
   │   └─ Uses existing Copilot Graph access (no app registration)
   │   └─ Downloads .txt attachments from DDG/iSEED folder
   │   └─ Stores in Input/Snapshots/ (idempotent)
   │
   ├─ Phase 2: Dashboard Refresh (PowerShell)
   │   └─ Runs: refresh-dashboard-snapshots-only.ps1
   │   └─ Parses snapshot CSV files
   │   └─ Validates safety checks (min records, regression detection)
   │   └─ Injects DATA into inventory-dashboard.html
   │   └─ Backs up previous version
   │
   ├─ Phase 3: Git Commit & Push
   │   └─ Creates feature branch: iseed/refresh-YYYYMMDD-HHMMSS
   │   └─ Commits with Copilot co-author trailer
   │   └─ Pushes to remote
   │
   └─ Phase 4: Pull Request & Auto-Merge
       └─ Creates PR via GitHub CLI
       └─ GitHub Actions (iseed-auto-merge.yml) auto-merges
       └─ Dashboard live on GitHub Pages (~1 min)
```

---

## Workflow Setup & Activation

### One-Time Setup (2 minutes)

**You only need to do this ONCE:**

1. Open the Copilot Workflow Editor (you should see a dialog)
2. Review the workflow configuration
3. Click **"Save"** (bottom right)
4. Done! ✅ Workflow is now active and scheduled

**That's it.** No other clicks needed.

### Do I Need to Click "Run in the Cloud"?

**NO.** Here's what those buttons do:

| Button/Option | Purpose | What You Should Do |
|---|---|---|
| **Save** | Activates the workflow to run automatically at 6 AM daily | ✅ **Click this** |
| **Run Now** | Runs the workflow immediately for testing (optional) | Only if you want to test before 6 AM |
| **Run in Cloud** | Same as "Run Now" but emphasizes it runs on cloud backend | Optional, same as above |

**Bottom line:** Just click **Save** and walk away. The workflow runs automatically every day.

### After You Save

- ✅ Workflow is active and scheduled for 6:00 AM daily
- ✅ Runs fully automatically (no more clicks needed)
- ✅ Your machine can be OFF
- ✅ No manual PRs or approvals needed
- ✅ Dashboard updates automatically

### Optional: Test Before First Run

If you want to test immediately (rather than wait until 6 AM):
1. After clicking Save, click "Run Now" in the workflow editor
2. Watch the logs in real-time
3. Verify each phase completes successfully
4. Check if PR was created and merged
5. Verify dashboard is updated

---

## Will It Auto-Create PRs and Merge?

**YES. Complete automated flow:**

| Step | What Happens | Automatic? |
|------|---|---|
| 1. Download snapshots | Graph API fetches .txt files | ✅ Yes |
| 2. Parse & update HTML | PowerShell script runs | ✅ Yes |
| 3. Git commit | Creates branch and commits | ✅ Yes |
| 4. GitHub PR created | `gh pr create` runs automatically | ✅ Yes |
| 5. PR auto-approved | GitHub Actions validates | ✅ Yes |
| 6. Auto-merged to main | Workflow squash-merges PR | ✅ Yes |
| 7. GitHub Pages publishes | Dashboard goes live | ✅ Yes |

**Zero manual approvals needed.** The entire process is fully automated.

---

## Will the Dashboard Always Get Updated?

**Short answer:** Yes, IF there are new snapshots to process.

**Detailed logic:**

| Condition | Result | PR Created? |
|-----------|--------|---|
| New .txt emails in DDG/iSEED folder | ✅ Downloads → Parses → HTML changes | **YES** → PR created & merged |
| No new emails (but old snapshots exist) | ✅ Runs script anyway with existing files | **MAYBE** - only if HTML changed |
| Fewer than 1,000 records parsed | ❌ Aborts (safety check) | **NO** - workflow stops |
| Record count drops >50% from previous | ❌ Aborts (regression detection) | **NO** - workflow stops |
| HTML doesn't change after parsing | ⏭️ Skips PR silently | **NO** - nothing to merge |
| HTML changes after parsing | ✅ Creates and merges PR | **YES** |

**Safety guardrails:**
- If parsed records < 1,000 → Aborts (prevents empty dashboard)
- If new records < (previous × 0.5) → Aborts (prevents data loss)
- Always backs up previous version before overwrite
- Never force-overwrites on validation failure

**Expected behavior:**
- If new data arrives → Dashboard updates automatically
- If no new data → Dashboard stays current with existing snapshots
- If data looks suspicious → Workflow aborts safely (manual review required)

---

## Your Machine Requirements

| Requirement | Needed? | Details |
|---|---|---|
| Machine always ON | ❌ **NO** | Workflow runs on Copilot Cloud Backend |
| Outlook installed | ❌ **NO** | Graph API used instead |
| Azure app registration | ❌ **NO** | Uses Copilot's existing access |
| Credentials to manage | ❌ **NO** | Session-level auth only |
| Manual PR approvals | ❌ **NO** | GitHub Actions handles it |
| Git/GitHub CLI pre-configured | ✅ **YES** | Should already be set up (for your manual work) |

**Bottom line:** Your machine can be completely OFF. Workflow doesn't depend on it.

### Daily Refresh Flow (6:00 AM UTC)

**Timeline:**

| Time | Phase | Action | Status |
|------|-------|--------|--------|
| 6:00 AM | Phase 1 | Copilot Workflow spawns on cloud backend | Auto ✓ |
| 6:00-6:05 AM | Phase 2 | Graph API downloads .txt from DDG/iSEED | Auto ✓ |
| 6:05-6:08 AM | Phase 3 | PowerShell parses snapshots, updates HTML | Auto ✓ |
| 6:08-6:10 AM | Phase 4 | Git: Create branch, commit, push | Auto ✓ |
| 6:10-6:12 AM | Phase 5 | GitHub CLI creates PR automatically | Auto ✓ |
| 6:12-6:14 AM | Phase 6 | GitHub Actions auto-approves & merges | Auto ✓ |
| 6:14-6:15 AM | Phase 7 | GitHub Pages publishes updated dashboard | Auto ✓ |

**Detailed Steps:**

1. **[6:00 AM]** Copilot Workflow Agent spawns automatically (no user action needed)
   - Runs on Copilot Cloud Backend
   - Your machine can be OFF
   - Fully autonomous, no approvals required

2. **[6:00-6:05 AM - Phase 1]** Graph API downloads attachments
   - Uses existing Copilot session auth (no credentials needed)
   - Fetches new .txt files from DDG/iSEED folder
   - Saves to `Input/Snapshots/` with timestamp naming
   - Idempotent: re-running doesn't duplicate files
   - If no new attachments found, continues with existing snapshots

3. **[6:05-6:08 AM - Phase 2]** PowerShell script parses and updates dashboard
   - Loads existing snapshot files from disk
   - Parses CSV records
   - Validates safety floors:
     - ✓ Minimum 1,000 records (aborts if fewer)
     - ✓ Regression detection (aborts if >50% drop from previous)
   - Injects data into HTML
   - Backs up previous version to Backups/ folder
   - Script fails safely (no overwrite on validation failure)

4. **[6:08-6:10 AM - Phase 3]** Automated commit and push
   - Creates feature branch: `iseed/refresh-YYYYMMDD-HHMMSS`
   - Stages changes: `git add inventory-dashboard.html`
   - Commits with audit trail and co-author trailer
   - Pushes branch to remote
   - Only if dashboard HTML actually changed

5. **[6:10-6:12 AM - Phase 4]** Pull Request created automatically
   - Uses GitHub CLI: `gh pr create --title "chore: auto-refresh ISEED dashboard" --base main`
   - No manual approval needed
   - PR links to this commit for traceability
   - Only if git push succeeded

6. **[6:12-6:14 AM - Phase 5]** GitHub Actions auto-merges
   - Existing workflow: `.github/workflows/iseed-auto-merge.yml`
   - Validates HTML markers (const DATA, const PRODUCT_CONFIG)
   - Auto-approves the PR
   - Squash-merges to main branch
   - Fully automatic, no manual review needed

7. **[6:14-6:15 AM - Phase 6]** GitHub Pages deploys
   - Dashboard automatically published to GitHub Pages
   - URL: https://nazmi-abd-ghani-intel.github.io/projects/ISEED-Volume-Analysis/inventory-dashboard.html
   - Live and accessible within ~15 minutes of workflow start

### Data Flow

```
DDG/iSEED Folder (Outlook Email)
   ↓ [Graph API downloads .txt attachments]
Input/Snapshots/*.txt (local snapshot cache)
   ↓ [PowerShell parses CSV]
Parsed records (JSON structure)
   ↓ [Inject into HTML]
inventory-dashboard.html (updated DATA constant)
   ↓ [Git commit + PR]
GitHub main branch (squash merged)
   ↓ [GitHub Pages]
https://...inventory-dashboard.html (Live Dashboard)
```

---

## Components

### 1. Copilot Workflow
**Scheduled:** Daily at 6:00 AM (Copilot Cloud Backend)

**Purpose:**
- Coordinates all phases: Graph collection → PowerShell refresh → Git/GitHub
- No setup required (uses existing Copilot Graph access)
- No stored credentials (session-level auth only)
- Runs reliably on cloud backend (no local scheduling)

**Output:** Logs summary of actions taken, PR link if created

---

### 2. Snapshot Refresh Script
**File:** `refresh-dashboard-snapshots-only.ps1`

**Purpose:**
- Parses snapshot files already in `Input/Snapshots/`
- Validates safety checks before updating dashboard
- Injects parsed data into HTML
- Backs up previous version

**Invoked By:** Copilot Workflow (Phase 2)

**Key Features:**
- No authentication needed (works offline on existing snapshot files)
- Safety guardrails: rejects updates if records look suspicious
- Detailed logging for troubleshooting
- Idempotent (safe to run multiple times)

---

### 3. GitHub Actions Workflow
**File:** `.github/workflows/iseed-auto-merge.yml`

**Purpose:**
- Auto-validates dashboard updates
- Auto-approves refresh PRs
- Auto-merges to main (squash strategy)
- Maintains git audit trail

**Triggers:**
- Pull request events targeting `main`
- Filters: Changes to `ISEED-Volume-Analysis/inventory-dashboard.html`

**Validations:**
- Checks file exists
- Verifies `const DATA=` marker
- Verifies `const PRODUCT_CONFIG=` marker

---

### 4. GitHub Pages
**URL:** `https://nazmi-abd-ghani-intel.github.io/projects/ISEED-Volume-Analysis/inventory-dashboard.html`

**Source:** Main branch, root folder (/)

**Deployment:** Automatic on every merge to main

---

## File Locations

| Component | Path | Purpose |
|-----------|------|---------|
| Copilot Workflow | Managed by Copilot | Daily 6 AM trigger + orchestration |
| Refresh Script | `refresh-dashboard-snapshots-only.ps1` | Parse snapshots & update dashboard |
| Dashboard | `inventory-dashboard.html` | Published dashboard |
| Snapshots | `Input/Snapshots/*.txt` | Email attachment cache |
| Product Config (Reference) | `Input/product-config.csv` | Mapping definitions |
| Product Config (Generated) | `Input/product-config.json` | Injected into dashboard |
| Backups | `Backups/` | Timestamped dashboard backups |
| GitHub Workflow | `.github/workflows/iseed-auto-merge.yml` | Auto-merge validation |

---

## Dashboard Access

**Public Link:**
```
https://nazmi-abd-ghani-intel.github.io/projects/ISEED-Volume-Analysis/inventory-dashboard.html
```

**Repository:**
```
https://github.com/nazmi-abd-ghani-intel/projects/blob/main/ISEED-Volume-Analysis/inventory-dashboard.html
```

---

## Monitoring & Troubleshooting

### Check Workflow Status
- Copilot will log a summary in the session after each run
- Check GitHub Actions for PR validation status
- Inspect recent commits in main branch for audit trail

### Common Issues

| Issue | Solution |
|-------|----------|
| No PR created | Check workflow logs. Usually: no new snapshots or no changes to dashboard |
| Dashboard not updating | Verify new .txt files in Input/Snapshots/. Check PowerShell script logs. |
| "Records < 1000" error | Snapshot folder empty or files too old. Check email folder for recent attachments. |
| "Data drop detected" | New record count dropped >50%. Manual review required before override. |
| GitHub Pages not live | Check GitHub Pages settings. Verify main branch is deployment source. |

---

## Safety Guardrails

**Workflow will abort if:**
- Parsed records < 1000 (safety floor)
- New records < (previous × 0.5) (regression detection)
- Git push fails (conflict/network)
- Snapshot directory is empty

**Workflow will skip silently if:**
- No new attachments downloaded
- Dashboard HTML unchanged after parsing

**Guarantees:**
- ✅ Never overwrites dashboard with suspicious data
- ✅ Always backs up previous version before overwrite
- ✅ All changes tracked in git with audit trail
- ✅ No secrets or credentials stored

---

## Dependencies

| Component | Version | Status |
|-----------|---------|--------|
| Copilot Workflow | Current | ✅ Cloud-based, auto-managed |
| Graph API Access | Current | ✅ Existing session auth |
| PowerShell | 5.0+ | ✅ Standard on Windows |
| Git CLI | 2.0+ | ✅ Standard dev tool |
| GitHub CLI (gh) | Latest | ✅ Standard dev tool |
| Azure App Registration | N/A | ❌ Not needed (no setup required) |
| Windows Task Scheduler | N/A | ❌ Not needed (cloud-based) |
| Outlook Desktop | N/A | ❌ Not needed (Graph API used) |

---

## Deployment Summary

| Aspect | Details |
|--------|---------|
| **Deployed** | 2026-09-21 |
| **Updated** | 2026-09-21 (switched from local scheduling to Copilot cloud workflow) |
| **Execution** | Copilot Cloud Backend (reliable, no local dependencies) |
| **Schedule** | Daily at 6:00 AM UTC (no user action needed) |
| **No Setup Required** | ✅ Uses existing Copilot Graph access + git/GitHub CLI |
| **No Azure Setup** | ✅ No app registration, no credentials to manage |
| **Monitoring** | Logs visible in Copilot session + GitHub Actions |

---

## What Changed from Previous Version

| Previous | Now |
|----------|-----|
| Local Windows Task Scheduler | Copilot Cloud Backend (6:00 AM daily) |
| Outlook COM (hung/failed) | Graph API via Copilot (reliable) |
| Required PowerShell script on machine | Minimal (only snapshot-parsing script needed) |
| Required Azure app registration | None (uses Copilot's existing access) |
| Required client secrets to store | None (session-level auth only) |
| IT approval/ticket needed | None |

---

## Audit Trail Example

Each automated refresh creates a commit like:

```
chore: auto-refresh ISEED dashboard [2026-09-21 06:00:00]

Automated snapshot refresh via Copilot Graph workflow.
Latest inventory data from DDG/iSEED folder.

Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>
```

All PRs numbered and linked for complete traceability.

---

## Questions or Issues?

Refer to the workflow instructions in Copilot for detailed step-by-step logic, or check GitHub Actions logs for PR validation details.

