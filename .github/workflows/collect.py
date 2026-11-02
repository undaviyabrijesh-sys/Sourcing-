"""Sourcing Radar: pharma tenders (GeM) and India API suppliers (WHO PQ list).
Each source is isolated, so one failing never stops the others. See data/run_report.txt."""
import io
import json
import os
import sys
import time

import pandas as pd
import requests

# Edit this list to the products you care about.
KEYWORDS = [
    "excipient",
    "active pharmaceutical ingredient",
    "microcrystalline cellulose",
    "hpmc",
    "lactose",
    "paracetamol",
    "pharmaceutical raw material",
]
WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
REPORT = []
OK = 0
os.makedirs("data", exist_ok=True)


def first(v):
    if isinstance(v, list):
        return v[0] if v else ""
    return "" if v is None else v


def gem_tenders(kw):
    s = requests.Session()
    s.headers.update(UA)
    s.get("https://bidplus.gem.gov.in/all-bids", timeout=30)
    token = s.cookies.get("csrf_gem_cookie", "")
    payload = {
        "page": 1,
        "param": {"searchBid": kw, "searchType": "fullText"},
        "filter": {"bidStatusType": "ongoing_bids", "byType": "all", "highBidValue": "", "sort": "Bid-End-Date-Latest"},
    }
    r = s.post(
        "https://bidplus.gem.gov.in/all-bids-data",
        data={"payload": json.dumps(payload), "csrf_bd": token},
        timeout=30,
    )
    r.raise_for_status()
    docs = r.json()["response"]["response"]["docs"]
    rows = []
    for d in docs:
        rows.append({
            "id": str(first(d.get("b_bid_number"))),
            "source": "GeM",
            "keyword": kw,
            "item": str(first(d.get("b_category_name"))),
            "buyer": f"{first(d.get('ba_official_details_minName'))} / {first(d.get('ba_official_details_deptName'))}",
            "ends": str(first(d.get("final_end_date_sort")))[:10],
            "link": "https://bidplus.gem.gov.in/showbidDocument/" + str(first(d.get("b_id"))),
        })
    return rows


def notify(rows):
    if not WEBHOOK or not rows:
        return
    for i in range(0, min(len(rows), 20), 5):
        text = "\n\n".join(
            f"**{r['item'][:120]}**\n{r['buyer'][:100]} | closes {r['ends']}\n{r['link']}" for r in rows[i:i + 5]
        )
        requests.post(WEBHOOK, json={"content": ("New tenders\n\n" + text)[:1900]}, timeout=20)
        time.sleep(1)
    if len(rows) > 20:
        requests.post(WEBHOOK, json={"content": f"+{len(rows) - 20} more in data/tenders.csv"}, timeout=20)


def run_tenders():
    global OK
    path = "data/tenders.csv"
    old = pd.read_csv(path, dtype=str).fillna("") if os.path.exists(path) else pd.DataFrame()
    seen = set(old["id"]) if len(old) else set()
    new = []
    for kw in KEYWORDS:
        try:
            rows = gem_tenders(kw)
            OK += 1
            REPORT.append(f"GeM '{kw}': {len(rows)} bids found")
            for r in rows:
                if r["id"] and r["id"] not in seen:
                    seen.add(r["id"])
                    new.append(r)
        except Exception as e:
            REPORT.append(f"GeM '{kw}': FAILED {type(e).__name__}: {str(e)[:150]}")
        time.sleep(2)
    if new:
        pd.concat([old, pd.DataFrame(new)], ignore_index=True).to_csv(path, index=False)
        try:
            notify(new)
        except Exception as e:
            REPORT.append(f"Discord: FAILED {str(e)[:100]}")
    REPORT.append(f"New tenders this run: {len(new)}")


def run_suppliers():
    global OK
    url = "https://extranet.who.int/prequal/medicines/prequalified/active-pharmaceutical-ingredients"
    try:
        html = requests.get(url, headers=UA, timeout=60).text
        df = max(pd.read_html(io.StringIO(html)), key=len)
        df.columns = [str(c).strip() for c in df.columns]
        col = next((c for c in df.columns if "country" in c.lower()), None)
        if col:
            df = df[df[col].astype(str).str.contains("India", case=False)]
        df.to_csv("data/suppliers_who_india.csv", index=False)
        OK += 1
        REPORT.append(f"WHO PQ API list: {len(df)} India rows")
    except Exception as e:
        REPORT.append(f"WHO PQ API list: FAILED {type(e).__name__}: {str(e)[:150]}")


if __name__ == "__main__":
    run_tenders()
    run_suppliers()
    text = "\n".join(REPORT)
    open("data/run_report.txt", "w").write(text)
    print(text)
    sys.exit(0 if OK else 1)
