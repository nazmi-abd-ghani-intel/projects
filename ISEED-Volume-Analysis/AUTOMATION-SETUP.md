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

### How it runs

- It is an **Automated cloud flow**: event-driven, not scheduled. The Outlook trigger watches `DDG/iSEED` and fires within ~1 minute of a mail landing there (Power Automate polls the mailbox; a mail *moved* into the folder counts too). Nothing to schedule and no PC involved — it runs in Microsoft's cloud 24×7.
- Runs are free (Standard connectors only). The generic **HTTP** connector is Premium and not licensed in this tenant, so the flow cannot write to GitHub directly — hence the SharePoint landing folder.
- Each run handles one mail and writes one file per attachment (normally 2: `central_inventory.txt`, `site_inventory.txt`).
- Health: make.powerautomate.com → **My flows** → *ISEED snapshot to SharePoint* → **28-day run history**. Failed runs also generate an e-mail from Power Automate. A flow that has not been triggered for 90 days can be turned off automatically — irrelevant here because mail arrives daily, but check the flow is still **On** after a long gap.

### Build / rebuild the flow

Flow name: `ISEED snapshot to SharePoint`. Owner: the mailbox owner (the trigger uses their Outlook connection).

**0. Clean-up (first time only)** — delete any older draft that contains an HTTP action, and revoke any GitHub PAT created for it.

**1. Create** — make.powerautomate.com → **Create** → **Automated cloud flow** → name it → search trigger `new email arrives` → **When a new email arrives (V3)** (*Office 365 Outlook*) → **Create**.

**2. Trigger** — open **Show advanced options** / *Advanced parameters* and set:

| Field | Value |
|---|---|
| Folder | The picker is usually empty. Switch the field to *custom value* (pencil / "Enter custom value") and paste the folder ID:<br>`AAMkADBmZWY4OGY1LWMwMDktNDNiOC1hM2NmLTZhMTdlMjZmZWFjOAAuAAAAAABIEEFTKb4BRLQLUI0nGFiAAQDQI2C36fGmRZCMSEK-w_EZAARQHQI7AAA=`<br>(= `DDG/iSEED`; re-read with `m365-graph-email_list_folders` if the mailbox is recreated) |
| From | `iseed_key_inventory@intel.com` |
| Include Attachments | **Yes** |
| Only with Attachments | **Yes** |
| everything else | default |

**3. Compose `stamp`** — **+ New step** → *Compose* (Data Operation). Rename the card to `stamp` (click the title or ⋯ → *Rename*; the name is referenced later). Click into **Inputs** → popup → **Expression** (*fx*) tab → paste → **Add**:

```
formatDateTime(triggerOutputs()?['body/receivedDateTime'],'yyyyMMdd-HHmmss')
```

This is the mail's received time in **UTC**; it becomes the filename prefix the parser reads.

**4. Apply to each** — **+ New step** → *Apply to each* (Control). In *Select an output from previous steps* → **Dynamic content** → under the trigger pick **Attachments** — the plain list item, **not** *Attachments Name* / *Attachments Content* (those are its children and only appear inside the loop). If only children are listed, search `Attachments` or click *See more*.

**5. Inside the loop → SharePoint – Create file** — *Add an action* → search `create file` → **Create file** (*SharePoint*):

| Field | Value |
|---|---|
| Site Address | `https://intel.sharepoint.com/sites/mpefusewg` (pick from list or *Enter custom value*) |
| Folder Path | folder icon → *Shared Documents* › *NVL Fuse Sync* › *Dynamic and Security Fuses* › *KeyIDs* › *Volume* › **KeysSnapshot**, or type `/Shared Documents/NVL Fuse Sync/Dynamic and Security Fuses/KeyIDs/Volume/KeysSnapshot` |
| File Name | three parts in order: **Expression** `outputs('stamp')` → *Add*; type a literal `-`; **Dynamic content** → *Attachments Name*. Renders as `[outputs('stamp')]-[Attachments Name]` |
| File Content | **Dynamic content** → *Attachments Content* (already base64 — no conversion needed) |

**6. Save** and clear any *Flow checker* errors (usually a required field left blank).

**7. Test** — in Outlook drag any old iSEED mail (with both `.txt` attachments) into `DDG/iSEED` → a run appears in the run history within a minute → two files like `20260915-050010-central_inventory.txt` show up in KeysSnapshot (SharePoint web or the synced folder on the VM). Optional immediate end-to-end: on the VM `Start-ScheduledTask 'ISEED Snapshot Sync'`, then watch the Actions tab.

If the flow is ever recreated by another person, the SharePoint file name convention and folder must stay identical; nothing downstream needs to change.

## Hop 2 — VM sync task (SharePoint → git)

| Item | Value |
|---|---|
| Script | `ISEED-Volume-Analysis/sync-snapshots.ps1` |
| Task Scheduler | `ISEED Snapshot Sync` — daily **06:00** local + **at logon (+2 min)**, *run task as soon as possible after a missed start*, 3 retries |
| Source | auto-discovered: `<OneDrive - Intel Corporation>\NVL Fuse Sync\Dynamic and Security Fuses\KeyIDs\Volume\KeysSnapshot` (override with `-SourcePath`) |
| Git | system git (`C:\Program Files\Git`) + Windows Credential Manager token — no Copilot app involved |
| Log | `ISEED-Volume-Analysis/Logs/sync-snapshots.log` (gitignored) |

### How it runs

1. **Find source** — locate the OneDrive root (`$env:OneDriveCommercial` → registry `HKCU\Software\Microsoft\OneDrive\Accounts\Business1` → any `OneDrive - *` folder) and append the KeysSnapshot relative path. The OneDrive sync client is what carries the file from SharePoint to disk — no API or token needed.
2. **Pick new files** — `*.txt` matching `yyyyMMdd-HHmmss-*.txt`, skipping anything already in `Input/Snapshots` (case-insensitive) or empty (0 bytes, i.e. still uploading).
3. **Safety** — abort if `Input/Snapshots` has uncommitted changes; `git fetch` → `checkout main` → `pull --ff-only`.
4. **Copy** — byte-for-byte (`ReadAllBytes/WriteAllBytes`; also hydrates OneDrive placeholder files).
5. **Commit** — `git add` only those paths; abort if anything else is staged; message `data(iseed): add N snapshot(s)`.
6. **Push** — one `pull --rebase` retry if the remote moved.
7. **Exit** — 0 = OK (including "Nothing to do", the normal case on most days), 1 = failure (task shows *Last Run Result* `0x1`; details in the log).

VM requirements: powered on and **signed in** (locked is fine) with the OneDrive sync client running. Neither Outlook nor the GitHub Copilot app needs to be open. If the VM was off at 06:00 the task runs as soon as it is back and you are logged on.

Useful commands:

```powershell
Get-ScheduledTaskInfo 'ISEED Snapshot Sync'            # LastRunTime / LastTaskResult / NextRunTime
Start-ScheduledTask   'ISEED Snapshot Sync'            # run now
Get-Content .\ISEED-Volume-Analysis\Logs\sync-snapshots.log -Tail 30
powershell -File .\ISEED-Volume-Analysis\sync-snapshots.ps1 -WhatIf   # dry run in the console
```

### One-time setup on a new VM

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

## Hop 3 — GitHub Actions rebuild (git → dashboard)

Workflow `.github/workflows/iseed-refresh.yml`, name *ISEED Dashboard Refresh*, runs on `windows-latest` (~2 min, free on a public repo). Triggers are listed under *Architecture*; the Hop 2 push is what fires it on a normal day.

### How it runs

1. **Checkout + inventory** — lists the snapshot files it is about to parse (visible in the job log / summary).
2. **Run injector** — `refresh-dashboard-snapshots-fast.ps1` parses every `Input/Snapshots/*.txt`, rebuilds `const DATA`, stamps `const LAST_UPDATED`, and enforces the safety floors (≥ 1000 records, no > 50 % drop).
3. **Encoding integrity check** — BOM present, zero U+FFFD replacement characters, 🌙 glyph intact, all script markers present. A failure here stops the run so a corrupted HTML is never published.
4. **Detect data change** — SHA256 of the `DATA` block before vs after. Identical (e.g. the nightly cron with nothing new) → changes discarded, no commit, summary says *DATA changed: False*.
5. **Commit and push** as `github-actions[bot]`: `chore(iseed): refresh dashboard …` with `[skip ci]` so it does not retrigger itself; `git pull --rebase` then push.
6. **GitHub Pages** redeploys `inventory-dashboard.html` within a minute or two; the page footer shows the new *Refreshed …* time.

## Normal day timeline (Asia/Kuala_Lumpur)

| Time | What happens |
|---|---|
| ~13:00 | iSEED mail (05:00 UTC) lands in `DDG/iSEED` → flow writes 2 files to KeysSnapshot → OneDrive mirrors them to the VM within minutes |
| 06:00 next day | Task Scheduler → `data(iseed): add 2 snapshots` pushed |
| ~06:02 | Actions rebuilds → `chore(iseed): refresh dashboard` |
| ~06:05 | Pages serves the refreshed dashboard |

Add a second daily trigger to the task (e.g. 14:00) if same-day publishing is wanted.

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

### Option 1: From GitHub Actions (Recommended)

Actions tab → **ISEED Dashboard Refresh** → **Run workflow** → branch `main`.

| Checkbox "Commit the refreshed dashboard" | Behaviour |
|---|---|
| ✅ ticked (default) | Normal run: rebuild → verify → commit to `main` if the data changed → Pages redeploys. |
| ⬜ unticked | **Dry run**: same steps, but the commit is skipped. Use after changing the script or the HTML template to confirm parsing, encoding check and "DATA changed" all pass without touching `main`. |

The checkbox exists only for manual runs; the `push` and `schedule` triggers always commit.

**Speed:** ~2 min. **Use case:** Test config changes, force refresh from existing snapshots, or dry-run the entire pipeline.

### Option 2: Locally (Parse Only, No Download)

```powershell
cd ISEED-Volume-Analysis
powershell -NoProfile -ExecutionPolicy Bypass -File .\refresh-dashboard-snapshots-fast.ps1
```

This parses existing snapshots in `Input/Snapshots/`, rebuilds the HTML locally, and **does not commit**. You decide afterward whether to `git add` and `git commit`.

**Speed:** ~30 sec. **Use case:** Local testing, debugging parsing logic, verifying HTML changes without touching git.

### Option 3: End-to-End (Download + Parse + Commit) — Legacy Script

**Skip all three hops and do everything in one script:**

```powershell
cd ISEED-Volume-Analysis
powershell -NoProfile -ExecutionPolicy Bypass -File .\refresh-inventory-dashboard.ps1 -Method Outlook -Unattended
```

What this does:
1. Downloads the latest iSEED mail attachments from Outlook (or Graph if specified)
2. Auto-renames them with `yyyyMMdd-HHmmss-<name>.txt` format using the mail's received time
3. Parses all snapshots in `Input/Snapshots/`
4. Rebuilds `inventory-dashboard.html` with safety checks
5. Commits to git if data changed: `chore(iseed): manual refresh`
6. Pushes to `main`

**Speed:** ~1–2 min (depends on Outlook response time). **Use case:** Force an immediate refresh without waiting for 06:00 or building Hop 1; useful fallback if Power Automate flow is broken.

**Parameters:**
```powershell
# Download from Outlook (requires desktop Outlook client)
.\refresh-inventory-dashboard.ps1 -Method Outlook -Unattended

# Download from Graph API (requires GraphClientId and interactive browser auth first time)
.\refresh-inventory-dashboard.ps1 -Method Graph -GraphClientId "<your-azure-app-id>" -Unattended

# Dry-run (parse, commit to staging, but don't push)
.\refresh-inventory-dashboard.ps1 -Method Outlook -Unattended # (manually push after reviewing)
```

**Requirements:**
- Outlook method: Desktop Outlook client must be installed and signed in
- Graph method: Azure AD app registration with `Mail.Read` permission (one-time setup)
- `-Unattended` flag: Suppresses interactive prompts (use for scheduled runs)

**When it fails:**
- Check `Logs/refresh-inventory-dashboard.log`
- Common issues: Outlook not running, folder path wrong, slow network

---

### Comparison: All Three Manual Options

| Aspect | Option 1: Actions | Option 2: Local PS (fast) | Option 3: Legacy Script |
|--------|---|---|---|
| **What it does** | Rebuild HTML from existing snapshots | Rebuild HTML locally | Download mail → Rebuild → Commit all in one |
| **Speed** | ~2 min | ~30 sec | ~1–2 min |
| **Needs internet?** | ✅ Yes (GitHub) | ❌ No | ✅ Yes (mail) |
| **Needs Outlook?** | ❌ No | ❌ No | ✅ Yes (Outlook method) |
| **Needs git push?** | ❌ Auto | ⚠️ Manual | ✅ Auto |
| **Commits to git?** | ✅ Yes (if data changed) | ❌ No (you decide) | ✅ Yes (if data changed) |
| **Skip Hop 1?** | No (use existing data) | No (use existing data) | ✅ Yes (downloads fresh) |
| **Best use** | Test config / dry-run | Debug parsing locally | Force immediate refresh / fallback if Hop 1 broken |



## Troubleshooting

| Symptom | Check |
|---|---|
| Dashboard not updating | Actions tab → latest *ISEED Dashboard Refresh* run. "DATA changed: False" means no new snapshots were committed → check the feeder. |
| Run failed at *Run injector* | Safety floor tripped (too few records / >50 % drop). Inspect the newest `.txt` files. |
| Run failed at *Encoding integrity check* | Someone edited the HTML with a lossy tool. Restore from the previous commit; never `Set-Content` the HTML. |
| No file in KeysSnapshot after a mail | Power Automate → flow → run history. No run: trigger folder/From filter or flow turned Off. Red run: open it — *Create file* usually fails on Folder Path or a blank File Name. |
| File in SharePoint but not on the VM | OneDrive client not running / paused, or the shortcut was removed. Open the folder in Explorer and check the sync icon. |
| Task *Last Run Result* `0x1` | Read `Logs/sync-snapshots.log`. Common: `Input/Snapshots` dirty, push rejected (credential expired → run `git push` once interactively). |
| Task never ran | VM off or nobody logged on at 06:00; it runs at next logon (+2 min). `Get-ScheduledTaskInfo 'ISEED Snapshot Sync'`. |