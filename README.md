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

2. sqlite3.OperationalError: table audio_submissions has no column named person_id

This occurred after implementing the phone-based linking in the audio application because the audio_submissions table was already created previously (prior to creation of person_id).
 Even if the schema has been changed, sqlite3's CREATE TABLE IF NOT EXISTS statement does nothing when the table already exists.

Search: sqlite3 CREATE TABLE IF NOT EXISTS doesn't update the schema
Solution: added code for PRAGMA table_info(audio_submissions) and ALTER TABLE ... ADD COLUMN as a fallback for when the database already exists.
Rejected: Deleting people.db and recreating it from scratch - although this works fine for tests,
 it's not a proper migration strategy that the application would require.


 3.
  Streamlit did not open automatically in browser (gio: http://localhost:8501: Operation not supported)

The Streamlit package attempted to launch a browser window using the "gio" command from Linux.
 But, I am operating inside WSL2 (Ubuntu), which lacks any built-in graphical interface browser application that can be opened through the gio command.

Searched: streamlit gio operation not supported WSL

Fix: Disregarded the issue (the warning is non-fatal – the server is running perfectly well) and simply opened http://localhost:8501 manually inside the Windows browser. Port forwarding from the localhost of WSL2 to Windows is done automatically.

Rejected: Installing some graphical browser and/or X server in WSL2 just to enable auto-launching of the browser window; that would have complicated things unnecessarily when all I have to do is spend 2 seconds in opening the link manually every time I start the server.




## Task 5 (Stretch): Scaling to 5,000 Gig Workers in a Weekend

This is an analysis of the system built above (Streamlit app + SQLite + local disk storage + a Flask API called by n8n). Not a generic scaling essay. Assuming about 5,000 submissions arrive over 48 hours unevenly (most in a few peak windows not spread evenly).

### What breaks

1. **SQLite write locking.** SQLite allows one writer at a time. Now every audio submission opens a new connection and writes directly. Under moderate concurrency (a few dozen simultaneous submissions) writes start queuing and some will fail with database is locked errors. This is certainly the first thing to break. It doesn't take 5,000 users, just 10-20 hitting Submit in the same few seconds.

2. **Streamlits execution model.** Streamlit reruns the script top to bottom on every user interaction and holds server-side session state per user. It was built for single-analyst dashboards, not thousands of public users. A single Streamlit process will run out of memory/CPU headroom before 5,000 concurrent sessions and theres no built-in horizontal scaling. You can't just spin up more Streamlit instances without also solving session/state sharing across them.

3. **Local disk storage for files.** Every submission currently writes its file to app/audio_uploads/ on a single machines disk. At scale this means: (a) the disk fills up unpredictably (b) if that single machine goes down all submissions and their audio are gone, (c) there's no redundancy or backup.

4. **Synchronous audio processing in the request path.** extract_audio_features() (via pydub/ffmpeg) runs inline blocking the HTTP request until it finishes. Under load slow feature extraction on lower-quality audio files would tie up server threads and cause request timeouts for other users waiting to submit.

5. **No duplicate-submission protection at the app level.** The n8n automation checks for duplicates when explicitly invoked but the Streamlit app itself doesn't call it. Someone could submit the recording 10 times (accidentally on a bad connection, retrying after a timeout) and create 10 rows.

### What I'd change before launch

- Replace SQLite with a managed Postgres instance (or at minimum enable SQLites WAL mode as a stopgap) to handle writes safely.

- Move audio storage to object storage (S3, Azure Blob or similar) instead of local disk. Durable doesn't fill up a single machine and can be served via CDN for playback.

- Decouple audio processing from the request path using a queue (e.g. A simple job queue or serverless function triggered on upload) so submission is instant and feature extraction happens asynchronously. Show the user "Submitted. Processing" than making them wait.

- Replace or front Streamlit with something built for concurrent public traffic. Either a lightweight API (FastAPI) + static frontend behind a proper web server or deploy Streamlit behind a load balancer with multiple instances and externalized session state if staying on Streamlit is a hard requirement.

- Add basic rate limiting and idempotency (e.g. debounce repeat submissions from the same phone number within a short window) to guard against accidental duplicate submissions and basic abuse/spam.

- Add monitoring/alerting for disk usage, error rates and queue backlog so problems are caught during the weekend not after.

- Cost: 5,000 submissions × an estimated 5-10MB average audio file is 25-50GB of storage plus egress if audio is played back frequently. Object storage + CDN costs for this volume are tens of dollars) but a single always-on VM sized for peak weekend load if left running afterward would be needlessly expensive. An autoscaling setup (scale up for the weekend down after) is the cost-sensible choice, over a fixed large instance.