# Quy tắc cho agent và công cụ hỗ trợ code

Đọc `TEAM_RULES.md` trước khi sửa code. Các quy tắc trong đó là quy ước chung của hai thành viên.

- Không commit secret, `.env`, môi trường `workspace-support/`, archive, model hoặc dữ liệu thực nghiệm lớn.
- Không thực thi package nghiên cứu; chỉ phân tích tĩnh trong môi trường cô lập.
- Không tự ý đổi schema, split, threshold, prompt hoặc test set.
- Chạy `python -m pytest -q` và `python -m ruff check src tests` trước khi bàn giao nếu dependency đã cài.
- Giữ thay đổi trong phạm vi task; cập nhật tài liệu khi thay đổi cách chạy hoặc contract.
- File văn bản dùng UTF-8 không BOM theo `.editorconfig`. Không ghi tiếng Việt qua pipeline PowerShell/Python khi chưa đặt encoding UTF-8; sau khi ghi phải đọc lại để kiểm tra dấu.
