# ISSUES AND FALLBACK LOG — SIH 2026 PS 26171

Every failure, diagnostic step, and fallback is logged here according to Iron Rule 4.

---

### ISSUE-001: Workspace Permission Restriction on D:\webman
* **Date:** 2026-09-20
* **Component:** Windows Workspace Setup (Phase 1)
* **Symptom:** `Access to the path 'D:\webman\PROGRESS.md' is denied.`
* **Diagnosis:** `D:\` drive root was provisioned with `BUILTIN\Administrators` and `NT AUTHORITY\SYSTEM` full control, but unprivileged user `saikalyan\cbsai` only had `ReadAndExecute`.
* **Resolution:** User granted Modify/Write security permissions on `D:\webman` via Windows Properties Security dialog. Verified write and execution.
* **Status:** RESOLVED.
