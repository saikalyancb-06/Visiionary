# SYSTEM ARCHITECTURE & DATA FLOW — PS 26171

```text
USER Instruction
 │
 ▼
BROWSER EXTENSION (Manifest V3)
 │
 ▼
LOCAL SCREEN + DOM CONTEXT
 │
 ├──────────────────┬────────────────────┬───────────────────┐
 ▼                  ▼                    ▼                   ▼
DOM/ATTRIBUTE   OCR + TEXT           LOCAL UI            LOCAL VISUAL
SENSITIVITY     VALIDATORS/NER       PERCEPTION          PII DETECTOR
RULES           (regex, Luhn,        (ONNX model)        (ONNX model:
                Verhoeff, PAN…)                          faces, images,
 │                  │                    │                canvas, etc.)
 └──────────────────┴─────────┬──────────┴───────────────────┘
                              ▼
                       PRIVACY ENGINE
        (union of regions + conservative policy + fail-closed)
                              │
        sensitive → REDACT · PII → MASK · safe UI → PRESERVE
                              ▼
           SANITIZED CONTEXT (image and/or structured elements)
                              ▼
              POST-REDACTION VERIFICATION (re-scan)
                              ▼
                  ┌────  EGRESS GATE  ────┐   ← single network choke point
                  │  PASS → send          │
                  │  FAIL → block + log   │
                  └───────────┬───────────┘
                              ▼
                      FASTAPI SERVER
                              ▼
                 VLM / LLM PROVIDER (replaceable)
                              ▼
        STRUCTURED ACTION (schema-validated on server AND client)
                              ▼
        LOCAL ACTION VALIDATOR → EXECUTOR (click/type/scroll/…)
                              ▼
          RE-OBSERVE → verify → next step or DONE   (closed loop)
```

## Trust Boundaries
1. **Local Zone (Trusted):** Extension context, offscreen document, ONNX runtime, privacy engine, vault, DOM executor.
2. **Egress Gate:** The sole network boundary (`src/egress/gate.ts`). No raw PII or unverified packages can cross this gate.
3. **Remote Zone (Untrusted):** FastAPI server & external LLM/VLM providers. Server receives only sanitized structured context and sanitized screenshots with PII redacted.
