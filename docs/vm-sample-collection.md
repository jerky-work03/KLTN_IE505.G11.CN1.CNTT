# Thu thập archive trên VM

Hai script dưới đây tải và xác minh **danh sách đã chọn**, không chọn lại mẫu, chia tập hoặc thực thi mã trong package. Chạy trong VM thu thập riêng. Archive, log và bảng kết quả nằm ngoài Git.

## Đầu vào

- Manifest npm có các cột `sample_id`, `package`, `version`, `artifact_filename`, `sha256`. SHA-256 phải là hash đã ghi trước khi tải.
- CSV chọn mẫu Datadog từ `scripts/select_malicious_samples.py`, có các cột `path`, `eco`, `cat`, `pkg`, `ver`, `date`.
- Clone metadata Datadog và **commit SHA đầy đủ** chứa các đường dẫn đã chọn. Không dùng nhánh thay đổi theo thời gian làm revision.

Chuẩn bị clone metadata, không checkout và không truy vấn kích thước mọi blob bằng `git ls-tree -l` vì có thể làm Git tải toàn bộ blob trong partial clone:

```bash
git clone --filter=blob:none --no-checkout --depth=1 \
  https://github.com/DataDog/malicious-software-packages-dataset.git data/external/datadog-meta
git -C data/external/datadog-meta rev-parse HEAD
```

Ghi lại SHA trả về và dùng đúng SHA đó cho bước tải. Nếu danh sách được chọn từ snapshot cũ, clone metadata phải có commit đó; không thay bằng HEAD mới.

## Tải và chạy tiếp

Ví dụ dưới đây sử dụng snapshot của lần thu thập đã hoàn tất; thay đường dẫn input/output bằng các file thuộc run của mình. Không dùng chung thư mục output giữa các run khác nhau.

```bash
python scripts/collect_vm_samples.py \
  --npm-manifest data/manifests/benign_npm_manifest.csv \
  --malicious-selection data/processed/selected_malicious.csv \
  --datadog-repo data/external/datadog-meta \
  --revision 72c723be547033c558244520524b117c8d71663b \
  --output-dir experiments/runs/vm-collection \
  --workers 4
```

Chạy lại cùng lệnh để tiếp tục. File đã khớp hash được giữ lại; file chưa hoàn chỉnh được tải lại qua file tạm. Script chỉ thay file đích sau khi tải xong và xác minh hash. Nếu đổi input hoặc revision, dùng output directory mới; hash cấu hình ngăn tái sử dụng nhầm run cũ. Lỗi tải trả exit code khác 0 và được ghi riêng trong CSV. Chạy lại không tự thay mẫu lỗi bằng gói khác.

Các giới hạn hiện tại: tối đa 100 MiB mỗi archive, 1–8 worker, dự phòng ít nhất 5 GiB dung lượng trống với một khoảng đệm trước mỗi lượt tải. Không tăng kích thước VM hoặc ổ đĩa tự động. URL phải dùng HTTPS và đúng registry/GitHub raw; redirect sang host khác bị từ chối.

Output bao gồm:

- `collection_config.json`: snapshot và SHA-256 của hai input.
- `npm_candidates_downloads.csv`, `malicious_downloads.csv`: kết quả tải và đường dẫn tương đối bên trong `raw/`.
- `raw/npm_candidates/`: archive npm khớp SHA-256 trong input.
- `raw/malicious/`: ZIP Datadog khớp Git blob hash của snapshot.

Nhãn ứng viên npm trong kết quả tải là `unknown`, chờ xác minh độc lập. Manifest input ban đầu được giữ nguyên. Hash xác minh tính toàn vẹn của archive, không chứng minh tính đúng đắn của nhãn. Với Datadog, SHA-256 là hash của **ZIP bên ngoài**; chưa phải hash của `.tgz`, `.whl` hoặc sdist bên trong. Ngày trong tên ZIP là ngày phát hiện, không tự coi là ngày phát hành.

## Xác minh sau khi tải

```bash
python scripts/verify_vm_samples.py \
  --npm-manifest data/manifests/benign_npm_manifest.csv \
  --malicious-selection data/processed/selected_malicious.csv \
  --datadog-repo data/external/datadog-meta \
  --output-dir experiments/runs/vm-collection
```

Script đối chiếu số lượng, từng record với input, SHA-256, kích thước, chữ ký định dạng và Git blob hash. Nó xuất `verification.json`; khi mọi mẫu đều đạt mới xuất `archive_checksums.sha256`. File checksum cũ bị bỏ nếu lần xác minh mới có lỗi. Không mở, giải nén, cài đặt hoặc chạy package. Cần bước phân tích tĩnh trong môi trường cô lập và quy trình xác minh nhãn riêng trước khi huấn luyện hay chia tập.

Trước khi chạy lâu trên VM dùng chung, ghi người chạy, run ID, thời gian dự kiến và thư mục output theo `TEAM_RULES.md`. Sau khi hoàn tất, kiểm tra không còn tác vụ của người khác trước khi deallocate VM.

## Lần thu thập ngày 19/11/2026

Run `20261119T053420Z-sample-both` đã dùng các script vận hành riêng trước khi mã được chuẩn hóa thành CLI ở trên. Input và snapshot được giữ nguyên; không chạy lại thí nghiệm trong thay đổi này.

| Nhóm | Archive đã tải và kiểm tra | Tổng byte |
| --- | ---: | ---: |
| npm ứng viên, nhãn chưa xác minh | 1.500 | 382.007.242 |
| npm độc hại từ Datadog | 1.500 | Gộp trong dòng dưới |
| PyPI độc hại từ Datadog | 1.500 | Hai nhóm Datadog: 927.507.220 |

Tổng cộng 4.500 archive. Kiểm tra đọc lại toàn bộ file không có lỗi hash; không có SHA-256 trùng trong từng nhóm. Chưa phân tích gần trùng và chưa tạo split. Bộ chọn Datadog dùng seed 42, một phiên bản mỗi gói. Project commit lúc thu thập: `b312f6cbf4d5e20b8d9c8c08d45d967f0f272daf`. VM đã được xác nhận deallocated sau khi xong. Manifest, archive và báo cáo chi tiết vẫn được giữ ngoài Git theo quy ước dự án.
