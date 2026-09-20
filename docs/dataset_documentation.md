# DATASET DOCUMENTATION — SIH 2026 PS 26171

Every dataset utilized in this project is documented here in accordance with Phase 3 specifications.

| Dataset | Source URL | Purpose | Train / Val / Test Usage | License | Notes / Limitations |
|---|---|---|---|---|---|
| **WebUI Subset** | https://github.com/divyanshushekhar/WebUI | UI Element Detection (buttons, inputs, links) | Train / Validation / Test | CC-BY-4.0 | Documented compact subset to preserve local GPU training budget. |
| **RICO** | https://interactionmining.org/rico | Cross-domain UI element robustness | Supplementary Validation | CC-BY-4.0 | Mobile UI origin; evaluated as supplementary baseline. |
| **Synthetic PII Corpus** | Local generator (`synthetic-data/`) | PII / Sensitive-Region Detection | Train / Val / Test (Template-split) | Permissive (Generated) | Exact DOM bounding boxes (`Range.getBoundingClientRect`), multi-locale (`en_IN`). |
| **Strata Insurance Sample** | Curated synthetic document set | Stress testing PII redaction | Robustness / Stress Only | Curated / Synthetic | Kept strictly held-out from training. |
| **VisualWebArena Subset** | Task benchmarks | E2E task evaluation | Evaluation Only | MIT | Programmatic task success checkers. |
