# Kết quả thiết lập máy ảo Azure

**Ngày xác minh:** 07/11/2026.

**Trạng thái bàn giao:** tạo máy thành công, Ubuntu khởi tạo xong, kết nối SSH từ máy Windows thành công. Máy đang chạy; lịch tự tắt hằng ngày đã bật.

## Thông tin kết nối

- Máy ảo: `vm-kltn-ubuntu`.
- Resource group: `rg-kltn`.
- Region thực tế: `centralindia`.
- IP công cộng: `20.219.139.171`.
- Tài khoản: `azureuser`.
- Cổng SSH: `22`.
- SSH host fingerprint đã xác minh qua Azure control plane: `SHA256:m7gvmMZLZAiWTSQA4Lyw7IWZRlYC8Qtw9ukY1qGF5Zk`.
- Kết nối được kiểm tra với `StrictHostKeyChecking=yes` và khóa SSH riêng trên máy Windows.

Chạy tại thư mục dự án:

```powershell
.\azure\Manage-KltnVm.ps1 -Action Connect
```

Nếu máy đã tự tắt, chạy `Start` trước khi `Connect`. Xem các lệnh quản lý trong [README](./README.md).

## Kết quả kiểm tra

| Hạng mục | Kết quả |
| --- | --- |
| Size | Standard_B2als_v2, 2 vCPU, 4 GiB RAM, x64 |
| Ubuntu image | Ubuntu Server 24.04 LTS Gen2, phiên bản `24.04.202610250` |
| Ổ hệ điều hành | 32 GiB, StandardSSD_LRS, đã gắn vào VM |
| Cloud-init | `status: done` |
| Python và venv | Python 3.12.3 |
| Git | 2.43.0 |
| Docker daemon | 29.1.3, truy vấn được bằng `sudo docker info` |
| Thư mục dự án | `/home/azureuser/kltn`, tài khoản `azureuser` ghi được |
| Xác thực mật khẩu SSH | Đã tắt |
| Trusted Launch | Secure Boot và vTPM đã bật |
| Tự tắt | Enabled, 16:00 UTC / 23:00 giờ Việt Nam |
| Quy tắc truy cập | Chỉ cổng 22 từ hai địa chỉ IPv4 `/32` đã xác minh của mạng hiện tại |
| Cổng 443 thử nghiệm | Đã đóng trong NSG và gỡ cấu hình SSH thử nghiệm trên Ubuntu |

Mạng hiện tại dùng địa chỉ ra Internet khác nhau giữa HTTP/SSH và HTTPS. Quy tắc đã được cập nhật theo hai địa chỉ được xác minh; SSH sau đó hoạt động. Script `AllowCurrentIp` đã chạy thành công và giữ truy cập ở mức địa chỉ cụ thể.

Network Watcher tại Central India đã được bật trong quá trình chẩn đoán IP flow. Không bật flow logs, Traffic Analytics, Bastion, Backup hoặc GPU.

## Phạm vi đã hoàn thành

Đã chuẩn bị máy ảo và công cụ nền. Chưa tải mẫu mã độc, chưa cài GuardDog/scikit-learn/XGBoost, chưa cấu hình khóa API LLM và chưa tạo container phân tích mẫu. Các phần này được thực hiện tiếp theo kế hoạch nghiên cứu.

Giá tham khảo CPU/RAM tại lúc kiểm tra: `0,0246 USD/giờ`, khoảng `17,96 USD/730 giờ`; ổ đĩa, IP và truyền dữ liệu tính riêng. Để kết thúc buổi làm việc, dùng `Stop` trong script và kiểm tra trạng thái deallocated.
