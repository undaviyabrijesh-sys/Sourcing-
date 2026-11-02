# Sourcing Radar

Collects pharma tenders from GeM and India API suppliers from the WHO prequalified API list. Runs on GitHub Actions twice a day and saves results in `data/`.

## Setup (works from a phone)
1. Create a new GitHub repo.
2. Add these files with **Add file > Create new file** (type the full path, e.g. `.github/workflows/collect.yml`): `collect.py`, `requirements.txt`, `.github/workflows/collect.yml`.
3. Optional alerts: make a Discord webhook, then in the repo go to **Settings > Secrets and variables > Actions > New repository secret**, name `DISCORD_WEBHOOK`.
4. Open the **Actions** tab, choose **Collect tenders and suppliers**, tap **Run workflow**.
5. Open the finished run. Check `data/run_report.txt` in the repo; it says which sources worked.

## Output
- `data/tenders.csv`: GeM tenders matching your keywords (new ones also go to Discord).
- `data/suppliers_who_india.csv`: Indian manufacturers on the WHO prequalified API list.
- `data/run_report.txt`: what worked and what failed.

Change the product keywords at the top of `collect.py`.
