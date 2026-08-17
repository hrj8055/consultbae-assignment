"""
Stage 5: Merge all 3 sources into ONE people table in SQLite.

Matching priority:
  1. email (normalized) links source1 <-> source2
  2. phone (normalized) links source1 <-> source3
  3. name + city (normalized) is a LAST-RESORT fallback, logged as
     low-confidence, for anyone who couldn't be matched by email/phone.
"""

import sqlite3
import pandas as pd
from normalize import normalize_phone, normalize_email, normalize_city, normalize_name

DB_PATH = "people.db"

# --- Load + drop obviously bad rows -----------------------------------------
naukri = pd.read_csv("data/source1_naukri_applicants.csv")
gig = pd.read_csv("data/source2_gig_workers.csv").dropna(how="all")  # drop blank row(s)
cbnexus = pd.read_csv("data/source3_cbnexus_contacts.csv")

# Drop the duplicate-header row hiding in source3
cbnexus = cbnexus[~cbnexus.astype(str).eq(cbnexus.columns.astype(str)).all(axis=1)]

# Drop the malformed/shifted row in source2 (a valid row's email_id should
# contain '@'; anything that doesn't is corrupted -- quarantine it)
bad_gig_rows = gig[~gig["email_id"].astype(str).str.contains("@", na=False)]
if len(bad_gig_rows) > 0:
    print(f"Quarantined {len(bad_gig_rows)} malformed row(s) from source2:")
    print(bad_gig_rows.to_string())
    bad_gig_rows.to_csv("pipeline/quarantined_rows.csv", index=False)
gig = gig[gig["email_id"].astype(str).str.contains("@", na=False)]

# --- Build normalized lookup keys on each dataframe -------------------------
naukri["norm_email"] = naukri["Email"].apply(normalize_email)
naukri["norm_phone"] = naukri["Phone"].apply(normalize_phone)
naukri["norm_name"] = naukri["Full Name"].apply(normalize_name)
naukri["norm_city"] = naukri["City"].apply(normalize_city)

gig["norm_email"] = gig["email_id"].apply(normalize_email)
gig["norm_name"] = gig["worker_name"].apply(normalize_name)
gig["norm_city"] = gig["location"].apply(normalize_city)

cbnexus["norm_phone"] = cbnexus["Phone Number"].apply(normalize_phone)
cbnexus["norm_name"] = cbnexus["Name"].apply(normalize_name)
cbnexus["norm_city"] = cbnexus["City"].apply(normalize_city)

# --- Build the master people list, starting from source1 as the hub --------
people = {}
match_log = []

next_id = 1
for _, row in naukri.iterrows():
    pid = next_id
    next_id += 1
    people[pid] = {
        "person_id": pid,
        "name": row["norm_name"],
        "email": row["norm_email"],
        "phone": row["norm_phone"],
        "city": row["norm_city"],
        "source_naukri": True,
        "source_gig": False,
        "source_cbnexus": False,
        "experience_years": row["Experience (Years)"],
        "skills": row["Skills"],
    }

email_index = {p["email"]: pid for pid, p in people.items() if p["email"]}
phone_index = {p["phone"]: pid for pid, p in people.items() if p["phone"]}

# Match source2 (gig workers) onto existing people via email
unmatched_gig = []
for _, row in gig.iterrows():
    pid = email_index.get(row["norm_email"])
    if pid:
        people[pid]["source_gig"] = True
        people[pid]["gig_rate"] = row["rate"]
        people[pid]["gig_status"] = row["status"]
        match_log.append({"file": "source2", "matched_on": "email",
                          "confidence": "high", "name": row["norm_name"]})
    else:
        unmatched_gig.append(row)

# Match source3 (CBNexus) onto existing people via phone
unmatched_cbnexus = []
for _, row in cbnexus.iterrows():
    pid = phone_index.get(row["norm_phone"])
    if pid:
        people[pid]["source_cbnexus"] = True
        people[pid]["verified"] = row["Verified"]
        people[pid]["projects_completed"] = row["Projects Completed"]
        match_log.append({"file": "source3", "matched_on": "phone",
                          "confidence": "high", "name": row["norm_name"]})
    else:
        unmatched_cbnexus.append(row)

# Fallback: name+city (LOW CONFIDENCE -- logged clearly)
name_city_index = {(p["name"], p["city"]): pid for pid, p in people.items()}

for row in unmatched_gig:
    key = (row["norm_name"], row["norm_city"])
    pid = name_city_index.get(key)
    if pid:
        people[pid]["source_gig"] = True
        match_log.append({"file": "source2", "matched_on": "name+city",
                          "confidence": "LOW", "name": row["norm_name"]})
    else:
        pid = next_id
        next_id += 1
        people[pid] = {
            "person_id": pid, "name": row["norm_name"], "email": row["norm_email"],
            "phone": None, "city": row["norm_city"], "source_naukri": False,
            "source_gig": True, "source_cbnexus": False,
        }
        match_log.append({"file": "source2", "matched_on": "NEW_PERSON",
                          "confidence": "n/a", "name": row["norm_name"]})

for row in unmatched_cbnexus:
    key = (row["norm_name"], row["norm_city"])
    pid = name_city_index.get(key)
    if pid:
        people[pid]["source_cbnexus"] = True
        match_log.append({"file": "source3", "matched_on": "name+city",
                          "confidence": "LOW", "name": row["norm_name"]})
    else:
        pid = next_id
        next_id += 1
        people[pid] = {
            "person_id": pid, "name": row["norm_name"], "email": None,
            "phone": row["norm_phone"], "city": row["norm_city"],
            "source_naukri": False, "source_gig": False, "source_cbnexus": True,
        }
        match_log.append({"file": "source3", "matched_on": "NEW_PERSON",
                          "confidence": "n/a", "name": row["norm_name"]})

# --- Write to SQLite ---------------------------------------------------------
people_df = pd.DataFrame(people.values())
match_log_df = pd.DataFrame(match_log)

conn = sqlite3.connect(DB_PATH)
people_df.to_sql("people", conn, if_exists="replace", index=False)
match_log_df.to_sql("match_log", conn, if_exists="replace", index=False)
conn.close()

# --- Summary ------------------------------------------------------------------
print("\n" + "=" * 60)
print("MERGE SUMMARY")
print("=" * 60)
print(f"Total unique people in master table: {len(people_df)}")
print(f"  - Present in Naukri:   {people_df['source_naukri'].sum()}")
print(f"  - Present in Gig:      {people_df['source_gig'].sum()}")
print(f"  - Present in CBNexus:  {people_df['source_cbnexus'].sum()}")
print(f"\nMatch log entries: {len(match_log_df)}")
print(match_log_df["confidence"].value_counts())
print(f"\nSaved to {DB_PATH}. Low-confidence matches and new-person entries")
print("are all visible in the match_log table for manual review.")