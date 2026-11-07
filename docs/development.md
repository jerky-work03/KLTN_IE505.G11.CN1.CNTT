# Quy trình phát triển

1. Tạo branch/task theo mã kế hoạch (`W02-N01`, `W05-H02`...).
2. Chạy unit test và lint trước commit.
3. Mỗi run lưu commit, config, seed, manifest hash, method/model/prompt version, thời điểm và predictions từng mẫu.
4. Chỉ chọn prompt, threshold và hyperparameter bằng train/validation; khóa test trước khi chạy chính.
5. Không đưa archive mã độc, API key hoặc output nhạy cảm vào Git.

```powershell
$env:PYTHONPATH = "$PWD/src"
python -m pytest
python -m ruff check src tests
```

## Mã hóa văn bản

Lưu file bằng UTF-8 không BOM theo `.editorconfig`. Khi dùng Windows PowerShell để gửi nội dung tiếng Việt qua pipeline sang Python, đặt `$OutputEncoding = [System.Text.UTF8Encoding]::new($false)` trước pipeline. Với Python, chỉ định `encoding="utf-8"` khi đọc/ghi file và đọc lại nội dung sau khi ghi để kiểm tra dấu.
