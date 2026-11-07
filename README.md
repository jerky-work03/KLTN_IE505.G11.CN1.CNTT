# Phát hiện gói thư viện độc hại trên npm và PyPI

Bộ khung Python cho khóa luận kết hợp phân tích tĩnh, học máy và LLM. Phạm vi và tiến độ nằm trong [kế hoạch](Ke_hoach_KLTN.md).

**Trạng thái:** đã có cấu trúc module, CLI trợ giúp/phiên bản, cấu hình nháp và quy ước dữ liệu. Các chức năng thu thập, quét, huấn luyện, gọi LLM và đánh giá chưa được triển khai. Chưa tải mẫu hoặc gọi API.

## Cấu trúc

```text
KLTN_Draft/
├── src/kltn/
│   ├── cli.py              # Entrypoint CLI
│   ├── contracts.py        # Hệ sinh thái, nhãn, trạng thái kết quả
│   ├── data/               # Thu thập, đọc archive, manifest, loại trùng, chia tập
│   ├── features/           # Đặc trưng tĩnh npm/PyPI và metadata
│   ├── baselines/          # GuardDog, Random Forest, XGBoost
│   ├── llm/                # Client, chọn file/ngữ cảnh, cache
│   ├── hybrid/             # Sàng lọc ML, routing LLM, decision rules
│   ├── evaluation/         # Metrics, coverage, chi phí, báo cáo
│   ├── robustness/         # Obfuscation, prompt injection, chấm giải thích
│   └── dependencies/       # Parser package-lock.json và requirements.txt
├── configs/                # Cấu hình môi trường và từng phương pháp
├── prompts/                # Zero-shot, few-shot, prompt kèm bằng chứng
├── schemas/                # Hợp đồng manifest, prediction, run và đặc trưng
├── data/                   # Archive, dữ liệu trung gian, manifests, splits
├── artifacts/              # Model, predictions, logs, báo cáo sinh ra
├── experiments/            # Ghi nhận run, quyết định và cấu hình đã khóa
├── scripts/                # Script chạy batch/tái lập
├── tests/                  # Unit, integration và fixture lành tính
├── notebooks/              # Khảo sát dữ liệu, phân tích lỗi
├── docs/                   # Kiến trúc, giao thức và hướng dẫn đóng góp
├── reports/                # Bản thảo, bảng và hình đã chọn
├── slides/                 # Slide bảo vệ
├── demo/                   # Kịch bản và đầu vào demo lành tính
├── docker/                 # Điểm đặt môi trường phân tích cô lập
└── azure/                  # Hạ tầng VM hiện có
```

Xem [kiến trúc và phân công module](docs/architecture.md), [quy ước dữ liệu](docs/data-contracts.md) và [quy trình phát triển](docs/development.md). Quy ước làm việc chung nằm trong [TEAM_RULES.md](TEAM_RULES.md); agent đọc thêm [AGENTS.md](AGENTS.md).

## Chạy bộ khung

Python 3.11 trở lên; khuyến nghị Python 3.12 trên VM Ubuntu. Python dùng cho ML sẽ được cố định sau pilot kiểm tra tương thích.

Windows PowerShell, không cần cài dependency để xem CLI:

```powershell
$env:PYTHONPATH = "$PWD/src"
python -m kltn --help
python -m kltn --version
```

Ubuntu/macOS:

```bash
PYTHONPATH=src python3 -m kltn --help
PYTHONPATH=src python3 -m kltn --version
```

Cài môi trường phát triển khi bắt đầu triển khai:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\kltn.exe --help
```

Các nhóm tùy chọn `ml` và `llm` chỉ cài khi cần. GuardDog sẽ được cố định phiên bản sau pilot và ưu tiên môi trường riêng. Chưa có dependency lock; không coi môi trường này là bản đã đóng băng để chạy test nghiên cứu.

## Quy ước lưu trữ

- `data/manifests/manifest.template.csv` là mẫu cột; chưa có dữ liệu thực nghiệm.
- `configs/experiments/*.toml` có trạng thái `draft`. Chưa chọn model LLM, ngưỡng hybrid hoặc mốc chia tập.
- Archive, dữ liệu sinh ra, model, log và cache được loại khỏi Git; thư mục giữ bằng `.gitkeep`.
- Kết quả dùng `malicious`, `benign`, `inconclusive`, `error`, `unsupported`; lỗi không được đổi thành nhãn lành tính.
- Mỗi run cần lưu commit, config/hash, seed, manifest/hash, phiên bản phương pháp và predictions từng mẫu.

Chỉ đọc tĩnh mẫu trong môi trường cô lập; không cài, build hoặc thực thi mã mẫu. Quy trình hạ tầng hiện tại nằm trong [hướng dẫn Azure](azure/README.md). Docker phân tích mẫu chưa được thiết lập.
