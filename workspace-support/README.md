# Tệp hỗ trợ workspace cục bộ

Thư mục này gom công cụ và tệp tạm phục vụ chuẩn bị dự án, tách khỏi mã nguồn nghiên cứu.

- `.codex-analysis/`: bản bảng kế hoạch và các bản trích nội dung phục vụ đối chiếu.
- `.codex-azure/`: môi trường Python/Azure CLI và tham số triển khai cục bộ. Không commit nội dung này.

Mã hạ tầng dùng chung vẫn ở `azure/`. Script `azure/Manage-KltnVm.ps1` đã trỏ tới vị trí Azure CLI mới. Dùng `python.exe -m azure.cli` và `python.exe -m pip` để chạy công cụ của môi trường này.

Thư mục `pytest-cache-files-5_6_xdsu` tại gốc là cache tạm bị Windows chặn quyền di chuyển. Nó được loại khỏi Git; chưa gom được vào đây.
