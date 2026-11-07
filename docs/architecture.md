# Ki?n tr?c module

```text
manifest -> archive reader -> static features -> detector adapters
                                      |-> GuardDog
                                      |-> RF/XGBoost
                                      |-> LLM
                                      `-> hybrid router -> prediction
prediction + run metadata -> evaluator -> tables/figures/report
```

`src/kltn/data` ch? t?o ??u v?o chu?n h?a v? kh?ng bi?t decision rule c?a detector. `src/kltn/features` tr? feature vector c?ng evidence v? coverage. `src/kltn/baselines`, `src/kltn/llm` v? `src/kltn/hybrid` d?ng chung prediction contract. `src/kltn/evaluation` ch? ??c predictions ?? l?u ?? tr?nh thay ??i k?t qu? khi t?nh l?i metrics.

## Ph?n c?ng

- **Ng? Th? ??c Nhu:** `data/`, `features/`, `baselines/ml.py`, schema feature, quality report.
- **Nguy?n Trung Hi?u:** `baselines/guarddog.py`, `llm/`, `hybrid/`, `dependencies/`, CLI v? demo.
- **C?ng ph? tr?ch:** `contracts.py`, evaluator, robustness, protocol, b?o c?o v? review.
