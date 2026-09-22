# ISEED Dashboard Automation

How `inventory-dashboard.html` is kept fresh without anyone touching it.

## Architecture

```
iseed_key_inventory@intel.com ──mail──▶ Outlook folder DDG/iSEED
                                            │
      ┌─────────────────────────────────────▼─────────────────────────────────────┐
      │ HOP 1 · Power Automate (cloud, Standard connectors only)                   │
      │  trigger: new mail in DDG/iSEED  →  SharePoint "Create file"                │
      │  mpefusewg › … › KeyIDs/Volume/KeysSnapshot/<yyyyMMdd-HHmmss>-<name>.txt   │
      └─────────────────────────────────────┬─────────────────────────────────────┘
                                            │ OneDrive sync client mirrors to disk
      ┌─────────────────────────────────────▼─────────────────────────────────────┐
      │ HOP 2 · VM · Task Scheduler "ISEED Snapshot Sync" (06:00 + at logon)       │
      │  sync-snapshots.ps1: copy new .txt → Input/Snapshots → commit → push main   │
      └─────────────────────────────────────┬─────────────────────────────────────┘
                                            │ push
      ┌─────────────────────────────────────▼─────────────────────────────────────┐
      │ HOP 3 · GitHub Actions · .github/workflows/iseed-refresh.yml                │
      │  refresh-dashboard-snapshots-fast.ps1 → encoding check → commit HTML → Pages │
      └───────────────────────────────────────────────────────────────────────────┘
```

No LLM in the pipeline; every hop only moves or transforms files deterministically. Each hop is independently recoverable: missed mails stay in SharePoint, missed syncs are picked up at the next task run, and the Actions cron rebuilds from whatever is committed.

Triggers for the Actions workflow:

| Trigger | When |
|---|---|
| `push` | any change under `ISEED-Volume-Analysis/Input/Snapshots/**` or `product-config.json` on `main` |
| `schedule` | daily 22:00 UTC = **06:00 Asia/Kuala_Lumpur** |
| `workflow_dispatch` | Actions tab → *ISEED Dashboard Refresh* → *Run workflow* (untick **commit** for a dry run) |

The Actions job never reads the mailbox. It only needs the `.txt` snapshots to be in git.

## Rules

- **Only the Actions job writes `inventory-dashboard.html`.** Feeders must commit `.txt` files (and optionally `product-config.json`) — nothing else. `sync-snapshots.ps1` aborts if anything else is staged.
- Never edit the HTML with `Get-Content`/`Set-Content`/`Out-File`; that destroys the emoji/arrow glyphs. The injector and the workflow both refuse to write a corrupted file.
- Snapshot filename convention: `yyyyMMdd-HHmmss-<attachment name>` using the mail's **UTC** received time, e.g. `20260921-110014-central_inventory.txt`. The parser reads the timestamp from the first 15 characters; the sync script ignores files that do not match.
- Never place the git repo inside a OneDrive-synced folder. SharePoint is the landing zone; git is the source of truth.

## Hop 1 — Power Automate flow (mail → SharePoint)

Uses only Standard connectors (the generic **HTTP** connector is Premium and not licensed in this tenant, so writing straight to GitHub is not possible).

1. make.powerautomate.com → **Create** → **Automated cloud flow** → name `ISEED snapshot to SharePoint`.
2. Trigger **Office 365 Outlook – When a new email arrives (V3)**
   - Folder: paste the folder ID (the picker is often empty):
     `AAMkADBmZWY4OGY1LWMwMDktNDNiOC1hM2NmLTZhMTdlMjZmZWFjOAAuAAAAAABIEEFTKb4BRLQLUI0nGFiAAQDQI2C36fGmRZCMSEK-w_EZAARQHQI7AAA=`
     (= `DDG/iSEED`; re-read it with `m365-graph-email_list_folders` if the mailbox is recreated)
   - From: `iseed_key_inventory@intel.com` · Include Attachments **Yes** · Only with Attachments **Yes**
3. **Compose** (rename `stamp`) → Expression
   `formatDateTime(triggerOutputs()?['body/receivedDateTime'],'yyyyMMdd-HHmmss')`
4. **Apply to each** → *Attachments* (the list item, not *Attachments Name*)
5. Inside the loop: **SharePoint – Create file**
   - Site Address: `https://intel.sharepoint.com/sites/mpefusewg`
   - Folder Path: `/Shared Documents/NVL Fuse Sync/Dynamic and Security Fuses/KeyIDs/Volume/KeysSnapshot`
   - File Name: `outputs('stamp')` + `-` + *Attachments Name*
   - File Content: *Attachments Content*
6. Save. Test by dragging any iSEED mail into `DDG/iSEED`; the file should appear in KeysSnapshot within a minute.

## Hop 2 — VM sync task (SharePoint → git)

| Item | Value |
|---|---|
| Script | `ISEED-Volume-Analysis/sync-snapshots.ps1` |
| Task Scheduler | `ISEED Snapshot Sync` — daily **06:00** local + **at logon (+2 min)**, *run task as soon as possible after a missed start*, 3 retries |
| Source | auto-discovered: `<OneDrive - Intel Corporation>\NVL Fuse Sync\Dynamic and Security Fuses\KeyIDs\Volume\KeysSnapshot` (override with `-SourcePath`) |
| Git | system git (`C:\Program Files\Git`) + Windows Credential Manager token — no Copilot app involved |
| Log | `ISEED-Volume-Analysis/Logs/sync-snapshots.log` (gitignored) |

What it does: finds `*.txt` matching `yyyyMMdd-HHmmss-*.txt` that are not yet in `Input/Snapshots`, copies bytes verbatim, `git add` only those paths, commits `data(iseed): add N snapshots`, pushes (one rebase retry). Aborts if `Input/Snapshots` is dirty or anything unexpected is staged. Exit 0 = OK (including "nothing to do"), 1 = failure (see log).

VM requirements: powered on and **signed in** (locked is fine) with the OneDrive sync client running. Neither Outlook nor the GitHub Copilot app needs to be open.

One-time setup on a new VM:
1. Open the KeysSnapshot folder in the browser → **Add shortcut to OneDrive** (or **Sync**).
2. Make sure `git push` works once interactively (stores the token in Credential Manager).
3. Register the task:
   ```powershell
   $s = 'C:\git-repo\nabdghan-git\projects\ISEED-Volume-Analysis\sync-snapshots.ps1'
   $a = New-ScheduledTaskAction -Execute powershell.exe -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$s`"" -WorkingDirectory 'C:\Program Files\Git\cmd'
   $t1 = New-ScheduledTaskTrigger -Daily -At 06:00
   $t2 = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"; $t2.Delay = 'PT2M'
   $st = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew
   Register-ScheduledTask 'ISEED Snapshot Sync' -Action $a -Trigger $t1,$t2 -Settings $st -Force
   ```
   Dry run any time: `powershell -File sync-snapshots.ps1 -WhatIf`

## Retired feeders

- **Copilot app workflow** (*ISEED Snapshot Feeder*, id `43561a25-…`): disabled 2026-09-22. It only ran while the GitHub Copilot desktop app was open, consumed AI credits per run, and an earlier version of its prompt hand-edited the HTML and corrupted it. Re-enable only as a temporary fallback.
- **Power Automate → GitHub HTTP**: not possible without a Premium licence.
- **Outlook Classic COM**: rejected — New Outlook is in use, and the classic cache did not sync `DDG/*`.
## Components

| Component | Purpose |
|---|---|
| `refresh-dashboard-snapshots-fast.ps1` | Parses `Input/Snapshots/*.txt`, injects `const DATA`, stamps `const LAST_UPDATED`, enforces safety floors (≥1000 records, no >50 % regression), refuses to write corrupted HTML, preserves BOM. |
| `.github/workflows/iseed-refresh.yml` | Runs the script in the cloud, verifies encoding, commits when data changed. |
| `.github/workflows/iseed-auto-merge.yml` | Legacy: validates & auto-merges PRs that touch the dashboard. Not used by the daily flow anymore; kept for manual PRs. |
| `inventory-dashboard.html` | Published via GitHub Pages (legacy build from `main`). Shows *Refreshed …* from `LAST_UPDATED`. |

## Manual refresh

### From GitHub (preferred)

Actions tab → **ISEED Dashboard Refresh** → **Run workflow** → branch `main`.

| Checkbox "Commit the refreshed dashboard" | Behaviour |
|---|---|
| ✅ ticked (default) | Normal run: rebuild → verify → commit to `main` if the data changed → Pages redeploys. |
| ⬜ unticked | **Dry run**: same steps, but the commit is skipped. Use after changing the script or the HTML template to confirm parsing, encoding check and "DATA changed" all pass without touching `main`. |

The checkbox exists only for manual runs; the `push` and `schedule` triggers always commit.

### Locally

```powershell
cd ISEED-Volume-Analysis
powershell -NoProfile -ExecutionPolicy Bypass -File .\refresh-dashboard-snapshots-fast.ps1
```
Then commit only if you have verified the output; or simply push new `.txt` files and let Actions do it.

## Troubleshooting

| Symptom | Check |
|---|---|
| Dashboard not updating | Actions tab → latest *ISEED Dashboard Refresh* run. "DATA changed: False" means no new snapshots were committed → check the feeder. |
| Run failed at *Run injector* | Safety floor tripped (too few records / >50 % drop). Inspect the newest `.txt` files. |
| Run failed at *Encoding integrity check* | Someone edited the HTML with a lossy tool. Restore from the previous commit; never `Set-Content` the HTML. |
| Power Automate HTTP 401/403 | Token expired or lacks *Contents: write*. |
| Power Automate HTTP 422 | File already exists — safe to ignore. |