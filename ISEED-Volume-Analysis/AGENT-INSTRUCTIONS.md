# Agent Instructions: ISEED Volume Analysis Automation

**Last Updated:** 2026-09-21  
**Status:** ✅ Automated via Copilot Cloud Workflow (No Agent Setup Required)

---

## Context

The ISEED dashboard automation is **fully configured** and runs on a daily schedule via a Copilot Cloud Workflow. This document is for:

1. **Future agents** working on ISEED tasks
2. **Reference** for understanding the current automation
3. **Troubleshooting** when things don't work as expected

---

## Current State

| Component | Status | Details |
|-----------|--------|---------|
| **Scheduled Workflow** | ✅ Active | Daily at 6:00 AM (Copilot Backend) |
| **Graph API Access** | ✅ Ready | Uses Copilot session (no app registration) |
| **Scripts** | ✅ Ready | `refresh-dashboard-snapshots-fast.ps1` |
| **GitHub Auto-Merge** | ✅ Ready | `.github/workflows/iseed-auto-merge.yml` |
| **Dashboard** | ✅ Live | Published on GitHub Pages |

**Nothing needs to be set up or configured. The workflow runs automatically.**

---

## If Agent Needs to Refresh Dashboard Manually

### Scenario 1: Immediate Refresh (Not Waiting for 6 AM)

Run the workflow manually:

```bash
# Assuming you have Copilot workflow access
# This executes the same daily workflow now (not at 6 AM)
```

**However:** If you're in an agent context, you can directly:

1. **Fetch attachments via Graph:**
   ```powershell
   # Use m365-graph-email tools to download from DDG/iSEED folder
   # Save to: projects/ISEED-Volume-Analysis/Input/Snapshots/
   ```

2. **Run the refresh script:**
   ```powershell
   cd projects/ISEED-Volume-Analysis
   powershell.exe -ExecutionPolicy Bypass -File refresh-dashboard-snapshots-fast.ps1
   ```

3. **Commit and PR:**
   ```bash
   git checkout -b iseed/refresh-manual-{timestamp}
   git add inventory-dashboard.html
   git commit -m "chore: manual ISEED dashboard refresh" ...
   git push -u origin iseed/refresh-manual-{timestamp}
   gh pr create --title "chore: manual ISEED dashboard refresh" --base main
   ```

### Scenario 2: Troubleshooting Failed Workflow

If the daily 6 AM workflow fails:

1. **Check Copilot logs** for error messages
2. **Verify iSEED folder** has recent emails with .txt attachments
3. **Check Input/Snapshots/** has recent snapshot files
4. **Run refresh script manually** (Scenario 1, step 2)
5. **Review safety check errors**:
   - `Records < 1000` → Snapshot files missing/old
   - `Data drop > 50%` → Investigate data integrity

---

## Script Differences: Which One to Use?

### `refresh-inventory-dashboard.ps1` (Original/Legacy)

**What it does:**
- ✅ Handles EVERYTHING in one script
- Downloads email attachments (Outlook COM or Graph)
- Parses snapshots
- Validates safety checks
- Updates dashboard
- Handles git/GitHub PR workflow

**When to use:**
- ⚠️ **NOT recommended** for current workflow
- Only use if you need full control + attachment fetching
- Requires Outlook COM (hangs on corporate machines) OR Azure app (blocked at Intel)

**Pros:**
- Complete all-in-one solution
- Includes attachment collection

**Cons:**
- Too complex for snapshot-only scenario
- Requires auth setup (Outlook/Graph)
- Part of failed Outlook COM approach

---

### `refresh-dashboard-snapshots-fast.ps1` (New/Lightweight)

**What it does:**
- ✅ Only parses existing snapshots
- ❌ Does NOT download attachments
- ✅ Validates safety checks
- ✅ Updates dashboard
- ❌ Does NOT handle git/GitHub (that's done by workflow)

**When to use:**
- ✅ **RECOMMENDED** for Copilot workflow
- Attachments are pre-downloaded by Copilot Graph tools
- Only needs to parse local .txt files
- No auth needed (works offline)

**Pros:**
- Lightweight (9KB vs 29KB)
- No authentication dependencies
- Fast (reads local files only)
- Safe (built-in validation)

**Cons:**
- Requires attachments already in Input/Snapshots/
- Doesn't handle PR creation (workflow does)

---

## Decision Tree: Which Script to Use

```
Do you have .txt files already in Input/Snapshots/?
│
├─ YES (files downloaded via Copilot or manually)
│   └─ Use: refresh-dashboard-snapshots-fast.ps1 ✅
│       └─ Fast, simple, no auth needed
│
└─ NO (need to fetch attachments from email)
    ├─ Can you run Graph queries? (have Copilot access)
    │   └─ Use: Copilot workflow
    │       └─ It handles attachment collection
    │
    └─ Need manual control?
        └─ Use: refresh-inventory-dashboard.ps1
            ├─ With -Method Outlook (needs desktop Outlook)
            ├─ Or -Method Graph (needs Azure app) ⚠️ Blocked
            └─ Not recommended for automated runs
```

---

## Architecture Diagram (For Agent Understanding)

```
Daily 6:00 AM Copilot Workflow
│
├─ Phase 1: Graph API Collection
│  ├─ m365-graph-email_list_folders
│  ├─ m365-graph-email_get (DDG/iSEED)
│  └─ m365-graph-email_attachments (→ Input/Snapshots/)
│
├─ Phase 2: Dashboard Refresh
│  └─ refresh-dashboard-snapshots-fast.ps1
│     ├─ Parse .txt files
│     ├─ Validate safety checks
│     └─ Inject into inventory-dashboard.html
│
├─ Phase 3: Git Commit
│  ├─ git checkout -b iseed/refresh-...
│  ├─ git add inventory-dashboard.html
│  └─ git commit + git push
│
└─ Phase 4: GitHub PR & Auto-Merge
   ├─ gh pr create
   └─ GitHub Actions auto-merge (iseed-auto-merge.yml)
```

---

## Safety Guardrails (Agent Must Respect)

### Abort Conditions (Never Override)

❌ **Do NOT update dashboard if:**
- Parsed records < 1000 (safety floor)
- New records < (previous × 0.5) (regression detection)
- Snapshot directory is empty
- CSV parsing fails on critical files

❌ **Do NOT force push or delete branches**

### Validation Steps (Always Perform)

✅ **Before updating dashboard:**
1. Count records in Input/Snapshots/*.txt files
2. Compare to previous embedded record count
3. If checks fail, abort and log error
4. Leave dashboard untouched (rollback-safe)

✅ **Before committing changes:**
1. Verify git status shows changes
2. Create feature branch (never commit to main)
3. Add git co-author trailer
4. Sign commits if enabled

---

## Troubleshooting Guide for Agents

### Issue: "Snapshot directory empty"

**Cause:** No .txt files downloaded  
**Fix:**
1. Check if Graph API collected attachments
2. Verify Input/Snapshots/ folder exists
3. Download files manually via Graph if needed
4. Re-run refresh script

### Issue: "Records < 1000"

**Cause:** Insufficient data  
**Fix:**
1. Check if new emails arrived in DDG/iSEED
2. Verify emails have .txt attachments
3. Wait for more data to accumulate
4. Do NOT override safety floor

### Issue: "Data drop > 50%"

**Cause:** Significant record count decrease  
**Fix:**
1. Investigate data source integrity
2. Check if snapshot files are corrupt
3. Compare with previous valid snapshot
4. Determine root cause before override
5. Manual review required

### Issue: "Git push failed"

**Cause:** Rebase conflict or network issue  
**Fix:**
1. Pull latest main: `git pull origin main`
2. Rebase feature branch: `git rebase main`
3. Resolve conflicts if any
4. Force push if needed (after verification)
5. Or abort and wait for manual review

### Issue: "PR not created"

**Cause:** GitHub CLI auth issue  
**Fix:**
1. Check GitHub CLI status: `gh auth status`
2. Re-authenticate: `gh auth login`
3. Verify token has repo access
4. Retry PR creation

---

## Key Points for Agents

✅ **Current state is fully automated** - no manual intervention needed  
✅ **Workflow runs daily at 6 AM** - check logs after that time  
✅ **Use snapshot-only script** for manual refreshes - it's safe and simple  
✅ **Always respect safety guardrails** - never override validation  
✅ **Git commits need co-author trailer** - maintains audit trail  
✅ **GitHub auto-merge handles PR closure** - don't manually merge  

❌ **Do NOT use refresh-inventory-dashboard.ps1** - legacy, requires auth  
❌ **Do NOT modify dashboard directly** - always go through script  
❌ **Do NOT skip safety checks** - they prevent bad data overwrites  
❌ **Do NOT commit to main branch** - always use feature branches  

---

## Contact / Escalation

If automation breaks:
1. Check Copilot workflow logs
2. Review GitHub Actions for PR validation
3. Inspect git commits for audit trail
4. Run refresh script manually for debugging
5. Check this document for troubleshooting steps

If manual intervention is needed:
1. Document the issue
2. Run manual refresh (Scenario 1 steps)
3. Review PR before merge
4. Investigate root cause
5. Update this document if patterns emerge
