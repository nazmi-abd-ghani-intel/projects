# ISEED Dashboard Automation

How `inventory-dashboard.html` is kept fresh without anyone touching it.

## Architecture

```
iseed_key_inventory@intel.com  ──mail──▶  Outlook folder DDG/iSEED
                                              │
                    ┌─────────────────────────┴──────────────────────────┐
                    │ FEEDER (pick one)                                   │
                    │  A. Power Automate flow  (cloud, PC can be off)     │
                    │  C. Copilot app workflow (runs on your PC)          │
                    │  → commits new .txt to Input/Snapshots/ on main     │
                    └─────────────────────────┬──────────────────────────┘
                                              │ push
                    ┌─────────────────────────▼──────────────────────────┐
                    │ .github/workflows/iseed-refresh.yml (GitHub Actions) │
                    │  windows-latest runner, no credentials needed        │
                    │  1. refresh-dashboard-snapshots-fast.ps1             │
                    │  2. encoding integrity check (BOM, U+FFFD, glyphs)   │
                    │  3. skip if DATA block unchanged                     │
                    │  4. commit inventory-dashboard.html → main           │
                    └─────────────────────────┬──────────────────────────┘
                                              │
                                    GitHub Pages redeploys
```

Triggers for the Actions workflow:

| Trigger | When |
|---|---|
| `push` | any change under `ISEED-Volume-Analysis/Input/Snapshots/**` or `product-config.json` on `main` |
| `schedule` | daily 22:00 UTC = **06:00 Asia/Kuala_Lumpur** |
| `workflow_dispatch` | Actions tab → *ISEED Dashboard Refresh* → *Run workflow* (untick **commit** for a dry run) |

The Actions job never reads the mailbox. It only needs the `.txt` snapshots to be in git.

## Rules

- **Only the Actions job writes `inventory-dashboard.html`.** Feeders must commit `.txt` files (and optionally `product-config.json`) — nothing else.
- Never edit the HTML with `Get-Content`/`Set-Content`/`Out-File`; that destroys the emoji/arrow glyphs. The injector and the workflow both refuse to write a corrupted file.
- Snapshot filename convention: `yyyyMMdd-HHmmss-<attachment name>` using the mail's **UTC** received time, e.g. `20260921-110014-central_inventory.txt`. The parser reads the timestamp from the first 15 characters of the filename.

## Feeder A — Power Automate (preferred)

Requires the **HTTP** action (Premium connector). If it shows a padlock in your tenant, use Feeder C.

1. **GitHub token** — github.com → Settings → Developer settings → Fine-grained tokens → *Generate new token*
   - Repository access: *Only select repositories* → `nazmi-abd-ghani-intel/projects`
   - Permissions → Repository → **Contents: Read and write**. Copy the token.
2. **Flow** — make.powerautomate.com → *Create* → *Automated cloud flow*
   - Trigger: **Office 365 Outlook – When a new email arrives (V3)**
     - Folder: `DDG/iSEED` · From: `iseed_key_inventory@intel.com`
     - Include Attachments: **Yes** · Only with Attachments: **Yes**
   - Action: **Compose** (rename to `stamp`) →
     `formatDateTime(triggerOutputs()?['body/receivedDateTime'],'yyyyMMdd-HHmmss')`
   - Action: **Apply to each** → *Attachments*
     - Inside: **HTTP**
       - Method: `PUT`
       - URI: `https://api.github.com/repos/nazmi-abd-ghani-intel/projects/contents/ISEED-Volume-Analysis/Input/Snapshots/@{outputs('stamp')}-@{items('Apply_to_each')?['name']}`
       - Headers:
         `Authorization` = `Bearer <token>` · `Accept` = `application/vnd.github+json` · `User-Agent` = `iseed-power-automate` · `X-GitHub-Api-Version` = `2022-11-28`
       - Body:
         ```json
         {
           "message": "data(iseed): add snapshot @{outputs('stamp')}-@{items('Apply_to_each')?['name']}",
           "branch": "main",
           "content": "@{items('Apply_to_each')?['contentBytes']}"
         }
         ```
         (`contentBytes` is already base64 — exactly what the GitHub API wants.)
     - Optional: HTTP → *Settings* → *Secure inputs* **On** so the token is not shown in run history.
3. Save, then forward yourself one old iSEED mail into `DDG/iSEED` to test. Within ~3 minutes you should see a `data(iseed):` commit followed by a `chore(iseed): refresh dashboard` commit from `github-actions[bot]`.

Notes: a duplicate filename returns HTTP 422 from GitHub — harmless (the file already exists). Two attachments arriving together produce two pushes; the Actions job serialises them via a concurrency group and rebases before pushing.

## Feeder C — Copilot app workflow (fallback)

The Copilot app scheduled workflow *ISEED Dashboard Auto-Refresh* runs **on your PC** (`hostId: local`) — the app must be open at run time. Under this architecture its prompt is reduced to:

1. Fetch mails from `DDG/iSEED` via Graph; save `.txt` attachments as `<UTC yyyyMMdd-HHmmss>-<name>.txt` into `Input/Snapshots/` (skip existing).
2. `git add ISEED-Volume-Analysis/Input/Snapshots/*.txt` → commit `data(iseed): add N snapshots` → `git push origin main`.
3. Do **not** run the refresh script or touch the HTML; the Actions job does that.

If the PC is off, no new snapshots land that day, but the 06:00 cron still runs harmlessly and the next successful feeder push catches up (all missed mails are still in the folder).

## Components

| Component | Purpose |
|---|---|
| `refresh-dashboard-snapshots-fast.ps1` | Parses `Input/Snapshots/*.txt`, injects `const DATA`, stamps `const LAST_UPDATED`, enforces safety floors (≥1000 records, no >50 % regression), refuses to write corrupted HTML, preserves BOM. |
| `.github/workflows/iseed-refresh.yml` | Runs the script in the cloud, verifies encoding, commits when data changed. |
| `.github/workflows/iseed-auto-merge.yml` | Legacy: validates & auto-merges PRs that touch the dashboard. Not used by the daily flow anymore; kept for manual PRs. |
| `inventory-dashboard.html` | Published via GitHub Pages (legacy build from `main`). Shows *Refreshed …* from `LAST_UPDATED`. |

## Manual refresh

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