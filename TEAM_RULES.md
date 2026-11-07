# Quy ước làm việc chung

**Dự án:** Nghiên cứu phát hiện gói thư viện độc hại trên npm và PyPI

**Thành viên:** Ngô Thị Đức Nhu và Nguyễn Trung Hiếu

**Mục tiêu của file:** giữ môi trường máy thật và máy ảo đồng bộ, tránh ghi đè dữ liệu hoặc làm sai kết quả thực nghiệm.

## 1. Nguyên tắc bắt buộc

1. Mọi thay đổi dùng chung phải đi qua Git. Không gửi cả thư mục môi trường hoặc archive qua Git.
2. Không commit API key, token, SSH key, `.env`, dữ liệu thô, archive mã độc, model lớn, cache hoặc log chứa thông tin nhạy cảm.
3. Không chạy `npm install`, `pip install`, build wheel hoặc script cài đặt của package nghiên cứu. Chỉ đọc tĩnh trong VM/container cô lập.
4. Không sửa test set, prompt, threshold hoặc hyperparameter sau khi đã xem kết quả test để làm đẹp kết quả. Nếu phải sửa, ghi rõ là exploratory run.
5. Lỗi phân tích không được đổi thành `benign`; dùng `inconclusive`, `error` hoặc `unsupported`.

## 2. Phân công mặc định

| Phần | Người chính | Thư mục/module |
|---|---|---|
| Dữ liệu, manifest, loại trùng, chia tập | Nhu | `src/kltn/data/`, `data/manifests/` |
| Đặc trưng tĩnh và ML | Nhu | `src/kltn/features/`, `src/kltn/baselines/ml.py` |
| GuardDog | Hiếu | `src/kltn/baselines/guarddog.py` |
| LLM, prompt, cache, retry | Hiếu | `src/kltn/llm/`, `prompts/` |
| Hybrid và dependency CLI | Hiếu | `src/kltn/hybrid/`, `src/kltn/dependencies/`, `src/kltn/cli.py` |
| Contract, evaluator, robustness, báo cáo | Cùng review | `src/kltn/contracts.py`, `evaluation/`, `robustness/`, `docs/` |

Người không phụ trách vẫn được sửa module của người kia khi có lý do rõ ràng, nhưng phải mở PR và thêm người phụ trách vào review.

## 3. Git và branch

- `main`: chỉ chứa code đã chạy kiểm tra; không commit trực tiếp.
- Tạo branch theo dạng `<nguoi>/<task>`:
  - `nhu/W02-data-manifest`
  - `hieu/W05-hybrid-routing`
  - `shared/W06-evaluation`
- Một branch chỉ phục vụ một mục tiêu. Không gom sửa code, đổi dữ liệu và đổi format báo cáo không liên quan.
- Trước khi bắt đầu:

```bash
git fetch origin
git switch main
git pull --ff-only
git switch -c <branch>
```

- Trước khi push, chạy test/lint và kiểm tra file sẽ commit:

```bash
python -m pytest -q
python -m ruff check src tests
git status --short
git diff --check
git diff --stat
```

- Commit dùng dạng ngắn, rõ mục đích: `data: add manifest validation`, `llm: record retry cost`.
- Không dùng `git push --force` trên `main` hoặc branch người khác. Nếu branch riêng cần force push, báo người còn lại trước.
- PR phải nêu: mục tiêu, file chính, cách kiểm tra, thay đổi contract/config và ảnh hưởng đến kết quả cũ.

## 4. Máy thật, máy ảo và môi trường riêng

- Mỗi máy có môi trường riêng: `.venv/`, `workspace-support/`, `.env` và cache không đồng bộ qua Git.
- Không commit đường dẫn tuyệt đối kiểu `C:\...` hoặc `/home/...`; dùng đường dẫn tương đối và biến môi trường.
- `azure/` là mã hạ tầng dùng chung. `workspace-support/.codex-azure/` là Azure CLI cục bộ, không phải mã dự án.
- Nếu hai người cùng dùng một VM, mỗi người dùng một clone/thư mục làm việc riêng. Không đổi branch trong clone của người kia.
- Trước khi chạy tác vụ tốn tài nguyên trên VM, ghi vào issue/PR: người chạy, run ID, thời gian dự kiến và thư mục output.
- Không xóa output hoặc container của người kia nếu chưa xác nhận.

## 5. Dữ liệu và artifact

Được commit:

- schema, template manifest, config không chứa secret, script, test fixture lành tính, tài liệu và bảng nhỏ đã kiểm tra.

Không được commit:

- `data/raw/`, `data/interim/`, `data/processed/`, `data/external/` thực tế;
- archive `.tgz`, `.tar.gz`, `.whl`, model, cache, prediction/log lớn;
- API response có secret hoặc nội dung package chưa được phép chia sẻ.

Mỗi run thực nghiệm phải lưu ngoài Git hoặc trong storage chung có quyền truy cập và có các thông tin:

- `run_id`, commit SHA, config hash, seed;
- manifest hash và snapshot nguồn;
- phiên bản GuardDog/model/prompt;
- predictions từng mẫu, metrics, coverage, latency, token, retry và chi phí;
- ghi chú thay đổi hoặc lỗi.

## 6. Contract không được tự ý phá vỡ

Các trường sau phải giữ ổn định hoặc tăng `schema_version` khi thay đổi:

- manifest: `sample_id`, `ecosystem`, `package`, `version`, `artifact_filename`, `sha256`, `label`, `label_basis`, ngày tháng, trạng thái;
- prediction: `sample_id`, `method`, `run_id`, `status`, `label`, `score`, `evidence`, latency, token, retry và error;
- status: `malicious`, `benign`, `inconclusive`, `error`, `unsupported`.

Thay đổi `src/kltn/contracts.py`, file schema, split hoặc decision rule hybrid cần được hai người review trước khi merge.

## 7. Quy tắc thực nghiệm

- Chia train/validation/test theo thời gian và khóa test trước khi chạy chính.
- Preprocessing, feature selection, threshold và prompt chỉ fit/chọn bằng train/validation.
- So sánh các phương pháp trên cùng tập mẫu; nếu LLM chạy subset thì mọi phương pháp trên subset đó phải dùng cùng danh sách.
- Báo riêng npm/PyPI, coverage, mẫu bị loại, `inconclusive`/`error` và chi phí retry.
- Không dùng GuardDog làm nguồn nhãn duy nhất rồi dùng chính nhãn đó để khẳng định hiệu quả GuardDog.

## 8. Cách xử lý conflict

1. Dừng merge; không chọn bừa một phía.
2. Gửi đoạn conflict và mục tiêu thay đổi cho người sở hữu module.
3. Giữ contract và dữ liệu đã được chốt; ưu tiên thay đổi nhỏ nhất.
4. Chạy lại test, `git diff --check` và một smoke test liên quan.
5. Ghi quyết định vào PR hoặc `experiments/README.md` nếu conflict ảnh hưởng kết quả.

## 9. Checklist trước khi merge

- [ ] Branch đúng task, không có file môi trường hoặc secret.
- [ ] Test/lint chạy thành công.
- [ ] Contract/schema không bị đổi ngầm.
- [ ] Config và output có version/run ID nếu ảnh hưởng thực nghiệm.
- [ ] README/docs đã cập nhật nếu thay đổi cách chạy.
- [ ] Người phụ trách module đã review.

## 10. GitHub account riêng cho dự án

- Repository này dùng GitHub account/organization riêng của dự án; không dùng nhầm account cá nhân hoặc account công ty.
- Chỉ cấu hình remote sau khi repository GitHub đã được tạo và xác nhận đúng owner.
- Mỗi máy phải kiểm tra identity trước commit:

```bash
git config user.name
git config user.email
git remote -v
```

- Không lưu password, personal access token hoặc private key trong repo. Dùng Git Credential Manager hoặc SSH key riêng cho account dự án.
- Nếu một máy dùng nhiều GitHub account, phải tách SSH host alias hoặc credential context; không dùng credential đang đăng nhập cho dự án khác.
- Trước khi push lần đầu, kiểm tra URL remote và quyền truy cập bằng một thao tác an toàn như `git ls-remote origin`.
- Không đổi owner, visibility hoặc branch protection của repository nếu chưa thống nhất cả hai người.
