"""
Stage 4: Normalization functions.

These turn messy, inconsistent values into a single canonical form so
the SAME person's data from different files can be compared and matched.
We import these functions into the merge script in Stage 5.
"""

import re

# --- Phone -----------------------------------------------------------------
def normalize_phone(raw):
    """
    Turns any of these into the same 10-digit string:
      '9000000254'        -> '9000000254'
      '+919000000254'     -> '9000000254'
      '09000000287'       -> '9000000287'
      '919000000260'      -> '9000000260'
      '+91-9000000131'    -> '9000000131'
    Strategy: strip everything except digits, then take the LAST 10 digits.
    """
    if raw is None:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) < 10:
        return None
    return digits[-10:]


# --- Email -------------------------------------------------------------------
def normalize_email(raw):
    """Lowercases and strips whitespace so casing differences don't matter."""
    if raw is None or (isinstance(raw, float)):
        return None
    email = str(raw).strip().lower()
    return email if email else None


# --- City --------------------------------------------------------------------
CITY_MAP = {
    "gurgaon": "Gurgaon",
    "gurugram": "Gurgaon",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "delhi ncr": "Delhi",
    "noida": "Noida",
    "pune": "Pune",
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
}

def normalize_city(raw):
    """'GURGAON', 'gurugram ', 'Delhi NCR' -> all become 'Gurgaon'/'Delhi' etc."""
    if raw is None:
        return None
    cleaned = str(raw).strip().lower()
    if not cleaned:
        return None
    return CITY_MAP.get(cleaned, cleaned.title())


# --- Name --------------------------------------------------------------------
def normalize_name(raw):
    """'RITU SHARMA' / 'ritu sharma' / '  Ritu Sharma  ' -> 'Ritu Sharma'"""
    if raw is None:
        return None
    cleaned = " ".join(str(raw).split())
    return cleaned.title() if cleaned else None


# --- Quick self-test when run directly --------------------------------------
if __name__ == "__main__":
    tests_phone = ["9000000254", "+919000000254", "09000000287",
                   "919000000260", "+91-9000000131"]
    print("Phone normalization:")
    for t in tests_phone:
        print(f"  {t!r:20} -> {normalize_phone(t)}")

    tests_email = ["ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG",
                   " isha.chopra95@mailtest.example.org "]
    print("\nEmail normalization:")
    for t in tests_email:
        print(f"  {t!r:40} -> {normalize_email(t)}")

    tests_city = ["GURGAON", "gurugram ", "Delhi NCR", "new delhi", "PUNE"]
    print("\nCity normalization:")
    for t in tests_city:
        print(f"  {t!r:15} -> {normalize_city(t)}")

    tests_name = ["RITU SHARMA", "ritu   sharma", "  Priya Singh  "]
    print("\nName normalization:")
    for t in tests_name:
        print(f"  {t!r:20} -> {normalize_name(t)}")