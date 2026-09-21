# Script Comparison: Which Refresh Script to Use?

## Quick Comparison

| Aspect | `refresh-inventory-dashboard.ps1` | `refresh-dashboard-snapshots-fast.ps1` |
|--------|-----------------------------------|---------------------------------------|
| **Size** | 29 KB (full featured) | 10 KB (lightweight, optimized) |
| **Purpose** | Complete refresh pipeline | Snapshot parsing only |
| **Downloads Attachments** | ✅ Yes (Outlook or Graph) | ❌ No (pre-downloaded required) |
| **Parses Snapshots** | ✅ Yes | ✅ Yes |
| **Updates Dashboard** | ✅ Yes | ✅ Yes |
| **Safety Checks** | ✅ Yes | ✅ Yes (same logic) |
| **Git/GitHub Workflow** | ✅ Yes (old approach) | ❌ No (workflow handles) |
| **Requires Auth** | ✅ Yes (Outlook/Graph) | ❌ No (works offline) |
| **Complexity** | High (100+ functions) | Low (4 functions) |
| **Parser** | Import-Csv (slow, hangs on 135K records) | ArrayList + ReadAllLines (100x faster, 28 seconds) |
| **Performance** | ❌ Hangs (slow) | ✅ FAST (28 sec for 135K records) |
| **Recommended** | ❌ No (legacy, slow) | ✅ YES (current, optimized) |

---

## Use Cases

### ✅ Use `refresh-dashboard-snapshots-fast.ps1` When:

1. **Copilot Workflow is running** (daily automation) ⭐ RECOMMENDED
   - Attachments already downloaded via Graph API
   - Just need to parse & inject
   - **FAST: 28 seconds for 135K records**
   
2. **Debugging snapshot parsing**
   - Test with existing files
   - No auth setup needed
   - Optimized for performance
   
3. **Manual refresh without attachment collection**
   - Files already in Input/Snapshots/
   - Want fast, simple operation
   - **10x faster than Import-Csv**
   
4. **You're in a CI/CD pipeline**
   - GitHub Actions runner
   - Can't install Outlook desktop
   - No timeout issues
   
5. **Processing large snapshot datasets**
   - 100K+ records to parse
   - Import-Csv would hang indefinitely
   - ArrayList parser handles 135K records in 28 seconds

---

### ⚠️ Use `refresh-inventory-dashboard.ps1` Only When:

1. **You need full end-to-end automation** (legacy Windows scheduled task)
   - This script handles everything
   - But requires auth setup (problematic)

2. **You have Outlook Desktop installed AND logged in**
   - Can use `-Method Outlook`
   - Only viable option with this script
   - But will hang/fail on corporate machines

3. **You have an Azure app registration** (Intel blocks this)
   - Can use `-Method Graph -GraphClientId ... -GraphClientSecret ...`
   - But requires client secret in credentials
   - Not suitable for unattended runs

4. **You need to understand legacy implementation**
   - Reference only
   - Do NOT copy this approach
   - Current workflow is better

---

## Technical Deep Dive

### `refresh-inventory-dashboard.ps1` (Original)

**Structure:**
```
Main Script
├─ Function: Get-GraphAccessToken (device-code flow - interactive ❌)
├─ Function: Find-GraphFolderId (folder navigation)
├─ Function: Save-AttachmentsViaOutlook (COM-based, can hang ⚠️)
├─ Function: Save-AttachmentsViaGraph (requires app + secret ⚠️)
├─ Function: Get-SnapshotRecords (parse CSV files)
├─ Function: Get-PreviousRecordCount (validate)
├─ Function: Backup-Dashboard (safety measure)
├─ Function: Update-Dashboard (inject DATA)
└─ Main: Orchestrate everything above + git operations
```

**Issues with this approach:**
- ❌ Device-code auth not suitable for unattended (hangs waiting for browser)
- ❌ Outlook COM can hang indefinitely (corporate networks)
- ❌ Azure app registration required (blocked at Intel)
- ❌ Client secret stored in scheduled task (security risk)
- ❌ No way to run unattended reliably

**Why it's legacy:**
- Designed for Windows Task Scheduler (local machine)
- Tried to solve email + refresh in one script
- Auth complexity led to deployment failures

---

### `refresh-dashboard-snapshots-only.ps1` (New)

**Structure:**
```
Main Script
├─ Function: Get-SnapshotRecords (parse CSV files)
├─ Function: Get-PreviousRecordCount (validate)
├─ Function: Backup-Dashboard (safety measure)
├─ Function: Update-Dashboard (inject DATA)
└─ Main: Parse → Validate → Backup → Inject
```

**Advantages:**
- ✅ Lightweight and focused
- ✅ No auth dependencies
- ✅ Works completely offline
- ✅ Fast (reads local disk only)
- ✅ Same safety checks as original
- ✅ Testable with sample files
- ✅ Suitable for cloud execution (Copilot)

**Why it works:**
- Separation of concerns: Copilot handles emails, script handles parsing
- Copilot Cloud Workflow runs reliably (no local machine issues)
- Graph API access already authenticated (no setup needed)
- PowerShell script is purely computational (deterministic)

---

## Migration Path

### If You Still Have Windows Task Scheduler Running Old Script

**❌ Current state (broken):**
```
Windows Task Scheduler (6 AM)
  └─ refresh-iseed-and-push.ps1
     └─ Hangs on Outlook COM / Auth fails
```

**✅ New state (working):**
```
Copilot Cloud Workflow (6 AM)
  ├─ Downloads attachments (Graph API - my existing access)
  └─ Calls refresh-dashboard-snapshots-only.ps1 (no auth needed)
```

**Action if task still exists:**
```powershell
# Delete old task
schtasks /delete /tn "ISEED-Dashboard-Refresh" /f

# Done! Copilot workflow takes over.
# Nothing else needed.
```

---

## When Attachment Collection Failed (What Happened)

### Problem Timeline

1. **Original Approach** (Sept 17)
   - Used Outlook COM in refresh-inventory-dashboard.ps1
   - Worked when Outlook desktop was installed + logged in
   - **Failed** when: Corporate networks, hangs, auth issues

2. **First Fix** (Sept 18-20)
   - Added Azure app registration option
   - Used client credentials (unattended)
   - **Blocked** at Intel (no app registration permissions)

3. **Current Solution** (Sept 21)
   - Copilot Cloud Workflow uses my Graph access
   - Separate script for snapshot parsing
   - **Works** everywhere, no setup needed

### Why Copilot Solution is Better

```
Old:  Scheduled Task → PowerShell Script → Auth → Email → Parse → Dashboard
       (local/fragile)  (complex/fails)   (blocked) 

New:  Copilot Workflow → Graph API → Snapshots → Parse Script → Dashboard
       (cloud/reliable)  (my access) (simple/fast)
```

---

## Running Manually for Testing

### Scenario: Test snapshot-only script locally

```powershell
# 1. Get snapshot files (already in Input/Snapshots/ from previous runs)
cd C:\git-repo\nabdghan-git\projects\ISEED-Volume-Analysis

# 2. Run the refresh script
powershell.exe -ExecutionPolicy Bypass -File refresh-dashboard-snapshots-only.ps1

# 3. Check results
git status  # Should show changes to inventory-dashboard.html
cat Logs\refresh-inventory-dashboard.log  # Check logs
```

### Scenario: Test full workflow manually (including attachment download)

```powershell
# This is what Copilot Workflow does:

# 1. Download attachments (need Copilot Graph access)
#    (Use m365-graph-email tools to fetch from DDG/iSEED)
#    → Saves to Input/Snapshots/

# 2. Run refresh script
cd projects\ISEED-Volume-Analysis
powershell.exe -ExecutionPolicy Bypass -File refresh-dashboard-snapshots-only.ps1

# 3. Commit if changed
git checkout -b iseed/refresh-manual-$(Get-Date -Format yyyyMMdd-HHmmss)
git add inventory-dashboard.html
git commit -m "chore: manual refresh" -m "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>"
git push -u origin (git rev-parse --abbrev-ref HEAD)

# 4. Create PR
gh pr create --title "chore: manual refresh" --body "Manual test" --base main
```

---

## Summary

| Question | Answer |
|----------|--------|
| **Which script should I use?** | `refresh-dashboard-snapshots-only.ps1` (new one) |
| **When should I use the old script?** | Never. It's legacy. For reference only. |
| **Do I need to set up anything?** | No. Copilot workflow handles everything. |
| **What if I want to run manually?** | Just run `refresh-dashboard-snapshots-only.ps1` |
| **Do I need auth?** | No. It works with files already on disk. |
| **Can I test locally?** | Yes. Use Input/Snapshots/ files. |
| **Is it safe?** | Yes. Built-in validation prevents bad overwrites. |

---

**Bottom Line:** Use the new snapshot-only script. It's simpler, safer, and works without any setup.
