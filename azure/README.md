# Môi trường Azure cho khóa luận

## Cấu hình

| Thành phần | Giá trị |
| --- | --- |
| Subscription | Azure for Students |
| Resource group | `rg-kltn` |
| Máy ảo | `vm-kltn-ubuntu` |
| Vùng tài nguyên | Central India |
| Size | `Standard_B2als_v2`: 2 vCPU, 4 GiB RAM, x64 |
| Hệ điều hành | Ubuntu Server 24.04 LTS, Gen2 |
| Ổ hệ điều hành | 32 GiB, Standard SSD LRS |
| Xác thực | Khóa SSH riêng, tắt xác thực bằng mật khẩu |
| Truy cập mạng | Chỉ mở SSH cổng 22 từ các địa chỉ IPv4 công cộng đã xác minh |
| Tự tắt | 23:00 giờ Việt Nam mỗi ngày, tương ứng 16:00 UTC |
| Công cụ cơ bản | Python, venv, Git, Docker, jq, ripgrep, unzip/zip |
| Thư mục làm việc | `/home/azureuser/kltn` |

Resource group có thể hiển thị vị trí Southeast Asia vì đã được tạo từ trước. Đây là vị trí metadata của group; vị trí máy ảo và các tài nguyên mới được cấu hình riêng là Central India.

`vm.template.json` mô tả hạ tầng; `cloud-init.yaml` mô tả khởi tạo Ubuntu. Thông tin xác thực Azure CLI nằm trong `%LOCALAPPDATA%\KLTN-AzureCLI`, không nằm trong repo. Tham số triển khai cục bộ nằm trong `workspace-support/.codex-azure` và được loại khỏi Git.

## Sử dụng từ PowerShell

Chạy tại thư mục `D:\UIT\HK4\KLTN_Draft`:

```powershell
# Xem trạng thái máy
.\azure\Manage-KltnVm.ps1 -Action Status

# Bật máy khi cần làm việc
.\azure\Manage-KltnVm.ps1 -Action Start

# Kết nối SSH sau khi máy khởi động
.\azure\Manage-KltnVm.ps1 -Action Connect

# Tắt và giải phóng CPU/RAM khi nghỉ
.\azure\Manage-KltnVm.ps1 -Action Stop

# Cập nhật quy tắc SSH sau khi đổi Wi-Fi hoặc IP mạng
.\azure\Manage-KltnVm.ps1 -Action AllowCurrentIp
```

Nếu đăng nhập Azure CLI hết hạn, dùng môi trường CLI đã tạo để đăng nhập lại:

```powershell
$env:AZURE_CONFIG_DIR = Join-Path $env:LOCALAPPDATA 'KLTN-AzureCLI'
.\workspace-support\.codex-azure\venv\Scripts\python.exe -m azure.cli login --use-device-code --output none
```

Khóa SSH riêng nằm ở `%USERPROFILE%\.ssh\kltn_azure_ed25519`. Không gửi tệp này cho người khác hoặc đưa vào Git. Máy khác cần khóa riêng và quy tắc truy cập riêng; không sao chép khóa cá nhân để dùng chung.

Mạng hiện tại có IP ra Internet khác nhau cho HTTP và HTTPS. `AllowCurrentIp` kiểm tra cả hai tuyến trước khi cập nhật các địa chỉ `/32`; không mở cả dải mạng. Nếu một lần kiểm tra thất bại, script giữ nguyên quy tắc hiện tại.

Tệp `%USERPROFILE%\.ssh\known_hosts_kltn` dùng để kiểm tra danh tính máy chủ. Nếu VM/IP được tạo lại, phải xác minh khóa máy chủ mới trước khi cập nhật tệp; không tắt kiểm tra SSH để bỏ qua cảnh báo.

## Làm việc trên Ubuntu

```bash
cd ~/kltn
source .venv/bin/activate
python --version
git --version
sudo docker version
```

Môi trường này mới chuẩn bị công cụ nền. Chưa tải mẫu mã độc, chưa cấu hình API LLM, chưa cài GuardDog/RF/XGBoost và chưa tạo container phân tích mẫu.

Chỉ tải và đọc tĩnh gói cần nghiên cứu. Không cài đặt, build hoặc thực thi gói mẫu trên VM. Trước khi thu thập mẫu, chuẩn bị container phân tích với giới hạn tài nguyên, không gắn thư mục nhạy cảm hoặc Docker socket và tách công đoạn cần mạng khỏi công đoạn phân tích.

## Chi phí

- Giá niêm yết CPU/RAM tại lúc kiểm tra ngày 07/11/2026 là `0,0246 USD/giờ`, tương đương khoảng `17,96 USD/730 giờ` tại Central India. Đây là giá tham khảo từ Azure Retail Prices API, không phải hóa đơn cam kết.
- Ổ đĩa, IP công cộng và truyền dữ liệu có thể tính phí riêng.
- Lệnh `Stop` trong script dùng `deallocate`; tắt Ubuntu bằng `shutdown` không thay thế bước giải phóng tài nguyên Azure.
- Khi máy deallocated, ổ đĩa và IP tĩnh vẫn có thể tính phí.
- Lịch tự tắt là lớp dự phòng. Sau khi làm xong nên chủ động chạy `Stop` và kiểm tra trạng thái.
- Không bật GPU, Azure Bastion, Backup hay dịch vụ tính phí bổ sung khi chưa cần.
- Kiểm tra credit và Cost analysis thường xuyên. Credit Azure không thanh toán mặc nhiên cho API LLM của nhà cung cấp bên ngoài.

## Xác minh sau triển khai

Kết quả kiểm tra và địa chỉ kết nối được lưu trong `deployment-status.md` sau khi máy được cấp và hoàn tất khởi tạo. Nếu chưa có tệp này, chưa coi môi trường là đã được kiểm tra xong.
