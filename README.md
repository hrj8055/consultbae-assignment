# ConsultBae AI Automation Assignment

## Setup

### Requirements

- Python 3.11+ (tested on 3.14)

- ffmpeg (`sudo install ffmpeg` on WSL/Ubuntu)

- Docker Desktop (for the n8n automation)

### Install

```bash

python3 -m venv venv

source venv/bin/activate

pip install pandas streamlit pydub mutagen

pip install audioop-lts # only needed on Python 3.13+

```

### Run the merge pipeline (Task 1)

```bash

python3 pipeline/explore.py # inspect raw data quality issues

python3 pipeline/normalize.py # self-test the normalization functions

python3 pipeline/merge.py # build people.db from all 3 sources

```

Outputs `people.db` (SQLite) in the project root, plus `pipeline/quarantined_rows.csv`

for rows that couldn't be safely parsed.

### Run the app (Task 3)

```bash

streamlit run app/audio_app.py

```

Open http://localhost:8501. Submit a name, phone and audio file (or record

in-browser). Every submission is matched to an existing person in `people.db`

by phone number. Creates a new person record if no match is found.

---

## Task 4: Data Issues Report

All issues below were found programmatically (see `pipeline/explore.py` output)

and confirmed by inspection of the CSVs.

### 1. No shared ID field across the 3 sources

- **Problem:** source1 (Naukri) has Email + Phone, source2 (gig workers) has

Email only source3 (CBNexus) has Phone. No single field links all three.

- **Fix:** Used source1 as a matching hub. Matched source2 via normalized

email, source3 via phone. Used name+city as a low-confidence

fallback for anything left unmatched logged separately than

silently merged (see `match_log` table in `people.db`).

### 2. Inconsistent phone number formats

- **Problem:** The same number appears as `9000000254` `+919000000254`

`09000000287` `919000000260` and `+91-9000000131` across files.

- **Fix:** `normalize_phone()` strips all -digit characters and keeps the

last 10 digits collapsing every variant to one canonical form.

### 3. Inconsistent email casing

- **Problem:** ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG` vs

`isha.chopra95@mailtest.example.org`. Same address, different case.

- **Fix:** `normalize_email()` lowercases and strips whitespace before matching.

### 4. Inconsistent city names

- **Problem:** source1 alone has 16 raw city strings that collapse

to far fewer real places. E.g. `Gurgaon`/`GURGAON`/`gurugram` (3+3 rows)

`Delhi`/`New Delhi`/`Delhi NCR` (4+4+2 rows) `Bangalore`/`Bengaluru` (4+3 rows).

5 rows also had leading/trailing whitespace ( "Noida "`).

- **Fix:** `normalize_city()` lowercases, strips whitespace and maps known

variants to one name via a lookup table.

### 5. Inconsistent name casing/spacing

- **Problem:** `RITU SHARMA` vs `Ritu Sharma` internal spaces, leading/

trailing whitespace.

- **Fix:** `normalize_name()` collapses whitespace and title-cases.

### 6. A blank row in source2 (gig_workers.csv)

- **Problem:** One row is entirely empty (all 6 columns null) which would

count as a "person" if loaded naively.

- **Fix:** Dropped with `df.dropna(how="all")` before any processing.

### 7. A duplicate header row embedded in source3 (cbnexus_contacts.csv)

- **Problem:** The literal header row (`Name,Phone Number,City,Verified

Projects Completed`) appears partway through the data body. Looks

like two files were concatenated without removing the second header.

- **Fix:** Detected any row whose values exactly match the column names and

removed it before processing.

### 8. A malformed/column-shifted row in source2

- **Problem:** One row has its columns shifted. The `email_id` column

actually contains skill tags (`react, javascript, mysql`) and the real

email appears in the position.

- **Fix:** Flagged any row whose `email_id` field doesn't contain `@` as

corrupted and quarantined it into `pipeline/quarantined_rows.csv`

of guessing how to realign the columns.

### 9. Inconsistent currency/rate units within the column

- **Problem:** `Current CTC` in source1 mixes two different units in the same

column. Some values look like annual rupees (e.g. `417964`) Others look

like LPA/lakhs (e.g. `4.2` `8.3`). 21 Of 42 rows (50%) have values under

100 strongly suggesting LPA. Similarly `rate` in source2 mixes `/hr`

(16 rows) and `k/month` (14 rows) formats, which're n't directly comparable.

- **Fix:** Did NOT attempt to convert/guess since the conversion

factor (LPA-to-annual hourly-to-monthly) isn't stated anywhere and getting

it wrong would be worse than leaving it ambiguous. Left both fields as

values in the merged DB and flagged this ambiguity here for manual

clarification before using either field for real analysis.

### 10. Inconsistent status/verified value formats

- **Problem:** `status` in source2 mixes casing (`Active`/`active`/`ACTIVE`/

`Inactive`/`paused`). `Verified` in source3 mixes `Y`/`N`/`yes`/`No`.

- **Fix:** Not required for matching so left as-is in the record but

noted here since a downstream consumer of this data should normalize these

too before filtering/reporting on them.

---

## Stuck Log

*(Fill in with your 2-3 hardest moments exactly what you searched what

you asked AI and what suggestions you rejected and why. This is graded and

"blank or generic stuck logs score zero.")*

**1. `ModuleNotFoundError: No module named 'audioop'` when using pydub**

- Python 3.14 removed the `audioop` module from the library, which

`pydub` depends on internally.

- Searched: [fill in exact search terms you used]

- Fix: installed `audioop-lts` a backport package that restores the same

module name, for Python 3.13+.

- Rejected: downgrading to an older Python version since that would've

meant rebuilding the whole venv and risked other compatibility issues.

