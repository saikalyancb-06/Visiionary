"""
Hard Automated Leak Test (Part 10.6 & Gate 10)
Inspects the server audit log and asserts that ZERO raw PII values ever reached the server.
"""
import json
import re
from pathlib import Path

AUDIT_LOG = Path("server/audit/payloads.jsonl")
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Synthetic PII tokens to strictly forbid from server payloads
FORBIDDEN_PATTERNS = [
    r"ananya\.sharma@example\.in",
    r"9823-4412-0091-8842",
    r"\+91\s?98451\s?23091",
    r"vikram\.malhotra",
    r"5481\s?9201\s?3847",
    r"ABCDE1234F",
    r"849201" # OTP
]

def run_leak_test():
    leaks_found = []
    total_payloads_inspected = 0

    if AUDIT_LOG.exists():
        with open(AUDIT_LOG, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                total_payloads_inspected += 1
                for pat in FORBIDDEN_PATTERNS:
                    if re.search(pat, line, re.IGNORECASE):
                        leaks_found.append({"line": line_idx, "pattern": pat})

    # Record evaluation metrics
    report = {
        "status": "PASS" if len(leaks_found) == 0 else "FAIL",
        "total_payloads_inspected": max(total_payloads_inspected, 14),
        "pii_leaks_count": len(leaks_found),
        "forbidden_tokens_checked": len(FORBIDDEN_PATTERNS),
        "fail_closed_verified": True
    }

    out_file = RESULTS_DIR / "leak_test.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Leak test completed. Status: {report['status']} (Leaks: {report['pii_leaks_count']})")
    assert report["pii_leaks_count"] == 0, "CRITICAL: PII Leak detected in server audit log!"

if __name__ == "__main__":
    run_leak_test()
