# Kiến trúc module

```text
manifest -> archive reader -> static features -> detector adapters
                                      |-> GuardDog
                                      |-> RF/XGBoost
                                      |-> LLM
                                      `-> hybrid router -> prediction
prediction + run metadata -> evaluator -> tables/figures/report
```

`src/kltn/data` chỉ tạo đầu vào chuẩn hóa và không biết decision rule của detector. `src/kltn/features` trả feature vector cùng evidence và coverage. `src/kltn/baselines`, `src/kltn/llm` và `src/kltn/hybrid` dùng chung prediction contract. `src/kltn/evaluation` chỉ đọc predictions đã lưu để tránh thay đổi kết quả khi tính lại metrics.

## Phân công

- **Ngô Thị Đức Nhu:** `data/`, `features/`, `baselines/ml.py`, schema feature, quality report.
- **Nguyễn Trung Hiếu:** `baselines/guarddog.py`, `llm/`, `hybrid/`, `dependencies/`, CLI và demo.
- **Cùng phụ trách:** `contracts.py`, evaluator, robustness, protocol, báo cáo và review.
