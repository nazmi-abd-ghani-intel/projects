# Manual Refresh Guide

## When to Run Manually

Use the PowerShell script directly when:

1. **Testing** - Verify script works before enabling automatic workflow
2. **Debugging** - Troubleshoot issues without waiting for 6 AM
3. **Emergency refresh** - Need immediate dashboard update
4. **Snapshot cache exists** - You have files in `Input/Snapshots/` already

**Do NOT use manual script for:**
- Regular daily updates (use automatic workflow instead)
- Downloading emails (script can't fetch emails, workflow does)
- Initial setup (workflow handles everything)

---

## Prerequisites

**Before running manually, ensure:**

1. ✅ PowerShell 5.0+ installed
2. ✅ Snapshot files exist in `Input/Snapshots/` folder
   ```powershell
   ls Input/Snapshots/  # Should show .txt files
   ```
3. ✅ Git CLI configured (for optional commit/push after)
4. ✅ GitHub CLI (gh) authenticated (for optional PR creation after)

---

## Running the Script

### Step 1: Open PowerShell

```powershell
# Navigate to project folder
cd C:\git-repo\nabdghan-git\projects\ISEED-Volume-Analysis
```

### Step 2: Run the Refresh Script

```powershell
powershell.exe -ExecutionPolicy Bypass -File refresh-dashboard-snapshots-only.ps1
```

### Step 3: Monitor Output

Watch for:
- ✅ "Successfully parsed X records"
- ✅ "Validated minimum record count"
- ✅ "Updated inventory-dashboard.html"
- ❌ "ERROR: Records < 1000" (abort - data looks bad)
- ❌ "ERROR: Data drop detected" (abort - regression detected)

### Step 4: Check Results

```powershell
# View script logs
cat Logs/refresh-inventory-dashboard.log

# Check if HTML changed
git diff inventory-dashboard.html  # Should show changes in DATA constant

# View backup
ls Backups/  # Previous version saved here
```

---

## After Script Runs Successfully

### Option A: Manual Git Commit & Push

```powershell
# 1. Create a feature branch
git checkout -b iseed/refresh-manual-$(Get-Date -Format yyyyMMdd-HHmmss)

# 2. Stage changes
git add inventory-dashboard.html

# 3. Commit
git commit -m "chore: manual refresh ISEED dashboard" `
  -m "Manually run snapshot refresh." `
  -m "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>"

# 4. Push
git push -u origin (git rev-parse --abbrev-ref HEAD)

# 5. Create PR (optional - if you want the same auto-merge flow)
gh pr create --title "chore: manual refresh ISEED dashboard" `
  --body "Manually run snapshot refresh" --base main

# 6. Check if PR auto-merged
gh pr view (last PR number)  # Should show merged status after ~2 minutes
```

### Option B: Skip Git (Just Update HTML Locally)

```powershell
# Script has already updated the HTML file
# You can just close PowerShell - changes are saved locally
# (They won't be in GitHub until you commit & push)
```

---

## Troubleshooting Manual Runs

### Issue: "Records < 1000"

**Cause:** Snapshot files are missing or too old

**Solution:**
```powershell
# 1. Check snapshot folder
ls Input/Snapshots/

# 2. If empty, use automatic workflow to download emails
# (Manual script can't fetch emails from Outlook)

# 3. For now, run manual refresh later after emails arrive
```

### Issue: "Data drop detected"

**Cause:** New record count < 50% of previous

**Solution:**
1. Check if snapshot files are recent: `ls Input/Snapshots/ -Attributes !d | Sort-Object LastWriteTime -Desc | Select-Object -First 3`
2. If files are old, wait for new emails
3. If files are new but data looks wrong, investigate snapshot content manually
4. To override safety check (NOT RECOMMENDED):
   - Edit `refresh-dashboard-snapshots-only.ps1` and temporarily increase the validation threshold
   - But this is risky - validates are there to prevent bad overwrites

### Issue: Script hangs or takes too long

**Cause:** Large snapshot files or slow disk I/O

**Solution:**
1. Check file sizes: `ls Input/Snapshots/ | Measure-Object -Property Length -Sum`
2. If >100 MB total, script may be slow (normal)
3. Wait 5-10 minutes for completion
4. If still hung after 15 minutes, kill process and check logs

### Issue: "inventory-dashboard.html didn't change"

**Cause:** Either data is identical to previous, or parsing failed

**Solution:**
1. Check logs: `cat Logs/refresh-inventory-dashboard.log`
2. If no errors: Data was identical (no new records, or same records)
3. If errors: See error message and check snapshot files
4. Re-run with fresh snapshots from workflow

---

## Comparing Manual vs Automatic

| Aspect | Manual Script | Automatic Workflow |
|--------|---|---|
| **Frequency** | One-time, on-demand | Every day at 6 AM |
| **Download emails** | ❌ No | ✅ Yes |
| **Parse snapshots** | ✅ Yes | ✅ Yes |
| **Update HTML** | ✅ Yes | ✅ Yes |
| **Create PR** | ⚙️ Optional (manual) | ✅ Automatic |
| **Auto-merge PR** | ⚙️ Optional (manual) | ✅ Automatic |
| **Your machine ON** | ✅ Required | ❌ Not needed |
| **Requires setup** | ❌ No | ✅ One-time "Save" |
| **Best for** | Testing, debugging | Daily production use |

---

## Example: Full Manual Workflow (Testing)

```powershell
# Scenario: Test the entire flow manually before enabling automatic workflow

cd C:\git-repo\nabdghan-git\projects\ISEED-Volume-Analysis

# 1. Run snapshot refresh
Write-Host "Phase 1: Running refresh script..."
powershell.exe -ExecutionPolicy Bypass -File refresh-dashboard-snapshots-only.ps1

# 2. Check if it changed
if (git diff --quiet inventory-dashboard.html) {
    Write-Host "No changes to dashboard"
} else {
    Write-Host "Dashboard updated! Creating PR..."
    
    # 3. Create feature branch
    $branch = "iseed/refresh-test-$(Get-Date -Format yyyyMMdd-HHmmss)"
    git checkout -b $branch
    
    # 4. Commit
    git add inventory-dashboard.html
    git commit -m "chore: manual test refresh" -m "Testing manual workflow"
    
    # 5. Push
    git push -u origin $branch
    
    # 6. Create PR
    Write-Host "Creating PR..."
    gh pr create --title "chore: manual test refresh" --body "Testing manual workflow" --base main
    
    # 7. Wait for auto-merge
    Write-Host "Waiting for auto-merge (2-3 minutes)..."
    Start-Sleep -Seconds 120
    
    # 8. Check result
    Write-Host "Checking if merged..."
    gh pr list --state closed --base main --limit 1
}

Write-Host "Test complete!"
```

---

## Questions or Issues?

- **Script errors:** Check `Logs/refresh-inventory-dashboard.log`
- **Git/PR issues:** Verify `git` and `gh` are configured: `git config --global user.name` and `gh auth status`
- **Missing snapshots:** Use automatic workflow instead (it downloads emails)
- **Safety validation failures:** Review the guardrails section in `AUTOMATION-SETUP.md`
