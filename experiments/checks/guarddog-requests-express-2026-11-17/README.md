# GuardDog smoke check: requests and express

- Run ID: `guarddog-requests-express-2026-11-17`
- Date: 2026-11-17 (Asia/Ho_Chi_Minh)
- Source commit: `b907447bc1901fba563d4ab6eaa7be08e6117ef5`
- Tool: GuardDog 3.2.0, kernel sandbox enabled
- Scope: exploratory smoke check, not a benchmark

| Ecosystem | Package | Version | Threat findings | Capability findings | Risk score |
| --- | --- | --- | ---: | ---: | ---: |
| PyPI | `requests` | 2.34.2 | 0 | 3 | 0.0 |
| npm | `express` | 5.3.0 | 0 | 1 | 0.0 |

No `threat-*` rule matched. The capability findings identify file, process, and network API patterns; they do not by themselves indicate malicious behavior. A zero GuardDog risk score is not a ground-truth benign label, so both predictions remain `inconclusive` under the project contract.

Package archive hashes/integrity values and the detailed findings are recorded in `manifest.json` and `predictions.jsonl`. The manifest digest is in `manifest.sha256`.
