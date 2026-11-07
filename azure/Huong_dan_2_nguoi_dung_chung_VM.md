# Hướng dẫn hai người dùng chung máy ảo Azure

Hai người có thể kết nối và làm việc đồng thời trên cùng VM. Mỗi người dùng tài khoản Ubuntu, khóa SSH, thư mục mã nguồn và môi trường Python riêng. Một người giữ quyền quản lý Azure để bật/tắt máy và quản lý truy cập.

Hướng dẫn này áp dụng cho VM đã tạo của nhóm. Các bước thêm người dùng dưới đây là hướng dẫn thực hiện; tài khoản người thứ hai chưa được tạo sẵn.

## 1. Thông tin máy và phân công

| Thành phần | Giá trị |
| --- | --- |
| Máy ảo | `vm-kltn-ubuntu` |
| Resource group | `rg-kltn` |
| Region | Central India |
| Hệ điều hành | Ubuntu Server 24.04 LTS |
| Tài nguyên dùng chung | 2 vCPU, 4 GiB RAM, SSD hệ điều hành 32 GiB |
| IP công cộng hiện tại | `20.219.139.171` |
| Cổng kết nối | SSH `22` |
| Tài khoản quản trị hiện có | `azureuser` |
| Tự tắt | 23:00 giờ Việt Nam mỗi ngày |

Phân công đề xuất:

| Người | Tài khoản Ubuntu | Quyền và trách nhiệm |
| --- | --- | --- |
| Người quản lý VM, ví dụ Hiếu | `azureuser` | Quản lý Azure, bật/tắt máy, cấu hình mạng và cài công cụ hệ thống |
| Người thứ hai, ví dụ Nhu | `nhu` | Kết nối SSH, quản lý mã nguồn và môi trường Python trong thư mục cá nhân |

Người thứ hai không cần được cấp tài khoản Azure hoặc nhận thông tin đăng nhập Microsoft của người quản lý. Nếu muốn dùng tên khác, thay `nhu` nhất quán trong các lệnh bên dưới.

## 2. Những việc chỉ cần làm một lần

Thứ tự thiết lập:

1. Người thứ hai tạo khóa SSH trên máy của mình.
2. Gửi **khóa công khai `.pub`** và các IP mạng hiện tại cho người quản lý.
3. Người quản lý tạo tài khoản Ubuntu, thêm khóa công khai và mở quy tắc mạng riêng.
4. Người thứ hai kiểm tra fingerprint máy chủ rồi đăng nhập.

Không chia sẻ khóa SSH riêng, mật khẩu Microsoft, mã MFA hoặc thư mục chứa phiên đăng nhập Azure CLI.

## 3. Người thứ hai tạo khóa SSH trên Windows

Mở PowerShell trên **máy của người thứ hai**. Kiểm tra đã có SSH:

```powershell
ssh -V
```

Nếu báo không tìm thấy `ssh`, cài tính năng **OpenSSH Client** trong Optional features của Windows trước khi tiếp tục.

Tạo khóa riêng cho đề tài:

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.ssh" | Out-Null

$kltnKey = Join-Path $env:USERPROFILE '.ssh\kltn_nhu_ed25519'
if (Test-Path -LiteralPath $kltnKey) {
    throw 'Khóa này đã tồn tại. Giữ nguyên khóa cũ hoặc chọn tên mới.'
}

ssh-keygen -t ed25519 -f $kltnKey -C 'nhu-kltn'
```

Khi được hỏi passphrase, nhập một cụm mật khẩu để bảo vệ khóa rồi nhập lại. Các ký tự nhập có thể không hiện trên màn hình.

Hai tệp được tạo:

| Tệp | Cách sử dụng |
| --- | --- |
| `%USERPROFILE%\.ssh\kltn_nhu_ed25519` | Khóa riêng, giữ trên máy cá nhân |
| `%USERPROFILE%\.ssh\kltn_nhu_ed25519.pub` | Khóa công khai, gửi cho người quản lý VM |

Xem fingerprint khóa công khai để người quản lý đối chiếu:

```powershell
ssh-keygen -lf "$env:USERPROFILE\.ssh\kltn_nhu_ed25519.pub"
```

Gửi **tệp `.pub`** và fingerprint này cho người quản lý qua kênh trao đổi của nhóm. Không gửi tệp không có đuôi `.pub`.

## 4. Xác định IP mạng của người thứ hai

Trên máy người thứ hai, chạy trong PowerShell:

```powershell
# IP ra Internet qua HTTP
curl.exe -4 --noproxy "*" --fail --silent --show-error http://checkip.amazonaws.com

# IP ra Internet qua HTTPS
curl.exe -4 --noproxy "*" --fail --silent --show-error https://api.ipify.org
```

Ghi lại cả hai kết quả. Nếu khác nhau, gửi cả hai địa chỉ cho người quản lý. Mạng đã dùng để thiết lập VM có IP khác nhau giữa HTTP/SSH và HTTPS; vì vậy chỉ kiểm tra IP trong trình duyệt có thể chưa đủ.

Nếu một lệnh lỗi, kiểm tra lại kết nối trước khi thay quy tắc mạng. Không tự thay bằng dải IP rộng hoặc `0.0.0.0/0`.

Ví dụ minh họa cách gửi thông tin:

```text
Tài khoản Ubuntu đề nghị: nhu
Khóa công khai: kltn_nhu_ed25519.pub
Fingerprint khóa SSH: kết quả lệnh ssh-keygen -lf trên máy của Nhu
IP HTTP: 203.0.113.10
IP HTTPS: 203.0.113.11
```

`203.0.113.10` và `203.0.113.11` chỉ là địa chỉ minh họa. Phải thay bằng kết quả thực tế; IP có thể thay đổi khi đổi Wi-Fi, VPN hoặc nhà mạng.

## 5. Người quản lý tạo tài khoản Ubuntu

### 5.1. Chuyển khóa công khai lên VM

Trước hết, người quản lý bảo đảm VM đã bật:

```powershell
cd D:\UIT\HK4\KLTN_Draft
.\azure\Manage-KltnVm.ps1 -Action Start
```

Trên Windows của người quản lý, lưu tệp `.pub` nhận được vào Downloads. Nếu lưu nơi khác, sửa đường dẫn nguồn trong lệnh sau.

```powershell
scp -i "$env:USERPROFILE\.ssh\kltn_azure_ed25519" -o "UserKnownHostsFile=$env:USERPROFILE\.ssh\known_hosts_kltn" -o StrictHostKeyChecking=yes "$env:USERPROFILE\Downloads\kltn_nhu_ed25519.pub" azureuser@20.219.139.171:~/kltn_nhu_ed25519.pub
```

Chỉ chuyển khóa công khai. Lệnh này dùng khóa quản trị đang có trên máy của người quản lý.

### 5.2. Đăng nhập tài khoản quản trị

Trên Windows của người quản lý:

```powershell
cd D:\UIT\HK4\KLTN_Draft
.\azure\Manage-KltnVm.ps1 -Action Start
.\azure\Manage-KltnVm.ps1 -Action Connect
```

Nếu VM đang chạy, có thể kết nối ngay. Những lệnh trong phần tiếp theo chạy **bên trong Ubuntu**, sau khi SSH thành công.

### 5.3. Xác minh khóa và tạo người dùng

Kiểm tra khóa nhận được:

```bash
ssh-keygen -lf ~/kltn_nhu_ed25519.pub
```

Fingerprint phải khớp kết quả người thứ hai đã gửi. Sau đó tạo tài khoản mới:

```bash
sudo adduser --disabled-password --gecos "" nhu
sudo chmod 750 /home/nhu
sudo install -d -o nhu -g nhu -m 700 /home/nhu/.ssh
sudo install -o nhu -g nhu -m 600 ~/kltn_nhu_ed25519.pub /home/nhu/.ssh/authorized_keys

sudo -u nhu mkdir -p /home/nhu/kltn
sudo -u nhu python3 -m venv /home/nhu/kltn/.venv
```

Đây là quy trình cho **tài khoản mới**. Nếu `nhu` đã tồn tại, kiểm tra trước; không chép đè `authorized_keys` của tài khoản đang sử dụng vì có thể xóa quyền truy cập bằng khóa cũ.

Tài khoản `nhu` đăng nhập bằng khóa SSH, chưa được thêm vào nhóm `sudo` hoặc `docker`. Không cần bật xác thực SSH bằng mật khẩu.

## 6. Người quản lý thêm quy tắc mạng riêng

Trên Azure Portal:

1. Tìm **Network security groups**.
2. Mở **vm-kltn-ubuntu-nsg** trong resource group **rg-kltn**.
3. Vào **Inbound security rules**, chọn **Add**.
4. Điền như bảng sau rồi lưu.

| Trường | Giá trị |
| --- | --- |
| Source | IP Addresses |
| Source IP addresses/CIDR ranges | Các IP thực tế của người thứ hai, mỗi địa chỉ thêm `/32`; nếu có hai địa chỉ, nhập cách nhau bằng dấu phẩy |
| Source port ranges | `*` |
| Destination | Any |
| Service | Custom, nếu cần để nhập cổng |
| Destination port ranges | `22` |
| Protocol | TCP |
| Action | Allow |
| Priority | `1010`, nếu chưa có quy tắc khác dùng số này |
| Name | `AllowSshNhu` |

Giữ nguyên quy tắc **AllowSshFromResearcher** của người quản lý. Khi IP của Nhu thay đổi, chỉ sửa **AllowSshNhu**.

Script `Manage-KltnVm.ps1 -Action AllowCurrentIp` hiện chỉ cập nhật **AllowSshFromResearcher**. Vì vậy:

- Người quản lý dùng script trên máy của mình để cập nhật IP quản trị.
- Người thứ hai gửi IP mới để người quản lý cập nhật quy tắc riêng.
- Không dùng script của người quản lý trên máy người thứ hai để thay IP cho cả nhóm.

Template `vm.template.json` hiện chỉ khai báo quy tắc của người quản lý. Trước khi triển khai lại template, phải bổ sung quy tắc của người thứ hai vào template; nếu không, lần triển khai lại NSG có thể xóa quy tắc thêm thủ công.

## 7. Người thứ hai kết nối lần đầu

Trên Windows của người thứ hai:

```powershell
ssh -o HostKeyAlgorithms=ssh-ed25519 -o IdentitiesOnly=yes -i "$env:USERPROFILE\.ssh\kltn_nhu_ed25519" nhu@20.219.139.171
```

Lần đầu, SSH hỏi có tin cậy máy chủ không. Đối chiếu fingerprint ED25519 với giá trị đã xác minh khi thiết lập VM:

```text
SHA256:m7gvmMZLZAiWTSQA4Lyw7IWZRlYC8Qtw9ukY1qGF5Zk
```

Chỉ nhập `yes` khi khớp. Nếu fingerprint khác, dừng và nhờ người quản lý xác minh lại; không tắt kiểm tra host key. Nếu VM đã được tạo lại, fingerprint có thể thay đổi hợp lệ nhưng vẫn phải xác minh qua Azure trước.

Khi SSH hỏi passphrase, nhập passphrase đã đặt cho khóa trên máy cá nhân. Đây không phải mật khẩu Microsoft hoặc mật khẩu Ubuntu.

Sau khi đăng nhập Ubuntu:

```bash
whoami
cd ~/kltn
source .venv/bin/activate
python --version
git --version
```

`whoami` phải trả về `nhu`. Dùng `exit` để kết thúc phiên SSH.

## 8. Kết nối nhanh và dùng VS Code

Trên máy người thứ hai, mở hoặc tạo tệp `%USERPROFILE%\.ssh\config`. Nếu đã có nội dung, **thêm** khối sau, không thay toàn bộ tệp:

```sshconfig
Host kltn-nhu
    HostName 20.219.139.171
    User nhu
    Port 22
    IdentityFile ~/.ssh/kltn_nhu_ed25519
    IdentitiesOnly yes
    HostKeyAlgorithms ssh-ed25519
```

Sau đó kết nối bằng:

```powershell
ssh kltn-nhu
```

Để sửa code bằng VS Code:

1. Cài extension **Remote - SSH** của Microsoft trên VS Code máy cá nhân.
2. Mở Command Palette, chọn **Remote-SSH: Connect to Host...**.
3. Chọn **kltn-nhu**.
4. Mở thư mục `/home/nhu/kltn` trên VM.

Code và các lệnh trong terminal remote chạy trên VM. Giao diện VS Code vẫn dùng RAM máy cá nhân; nếu máy yếu, dùng SSH trong PowerShell sẽ nhẹ hơn. Hai phiên VS Code remote cũng tiêu thêm RAM trên VM, nên mở vừa đủ cửa sổ.

## 9. Làm việc chung bằng Git

Mỗi người có bản clone riêng trong thư mục của mình. Ví dụ chạy **trên Ubuntu**:

```bash
cd ~/kltn
# Thay YOUR_REPOSITORY_URL bằng URL repo thật của nhóm.
git clone YOUR_REPOSITORY_URL source
cd source
git switch -c nhu/data-pipeline
```

Người quản lý làm tương tự trong `/home/azureuser/kltn` với nhánh riêng, ví dụ `hieu/llm-pipeline`.

- Mỗi người tự cấu hình tên/email Git và phương thức xác thực GitHub của mình.
- Xem `git status` trước khi đổi nhánh hoặc pull. Commit phần đang làm trước khi tích hợp thay đổi từ người khác.
- Đẩy nhánh lên repo và review thay đổi trước khi merge.
- Không sửa đồng thời cùng một thư mục clone dưới một tài khoản chung.
- Không đưa khóa SSH riêng, `.env`, API key, `.venv`, phiên đăng nhập Azure hoặc archive mã độc vào Git.
- Dữ liệu lớn cần thống nhất một nơi lưu phù hợp; không tạo nhiều bản sao archive làm đầy ổ 32 GiB.

Không cần chia sẻ thư mục của người quản lý hoặc tài khoản Azure để dùng chung repository.

## 10. Python, Docker và tài nguyên dùng chung

### Python

Mỗi người kích hoạt môi trường của mình:

```bash
cd ~/kltn
source .venv/bin/activate
```

Cài thư viện công cụ bằng pip trong venv theo danh sách dependency đã thống nhất. **Không cài gói mẫu đang điều tra** bằng `pip install`, `npm install`, build wheel hoặc chạy script cài đặt của mẫu.

### Docker

Docker đã cài trên VM; tài khoản quản lý hiện dùng `sudo docker ...`. Tài khoản `nhu` chưa có quyền điều khiển Docker daemon.

Việc thêm người dùng vào nhóm `docker` cấp quyền gần tương đương root. Với cấu hình ban đầu, người quản lý chuẩn bị và điều phối container phân tích; không tự thêm quyền Docker/sudo chỉ để bỏ lỗi permission. Nếu cần giao quyền cho cả hai, phải thống nhất mô hình quyền và cách cô lập mẫu trước.

Container phân tích mẫu cần có giới hạn CPU/RAM, không gắn Docker socket hoặc thư mục chứa khóa SSH/API key, và tắt mạng ở công đoạn không cần mạng. Hiện chưa có container phân tích mẫu được tạo sẵn.

### CPU, RAM và ổ đĩa

Tổng tài nguyên vẫn là **2 vCPU/4 GiB RAM** cho cả hai. Sắp lịch để tránh chạy đồng thời hai đợt huấn luyện hoặc quét lớn.

Các lệnh xem tài nguyên trong Ubuntu:

```bash
free -h
df -h /
top
```

Nếu máy chậm hoặc thiếu RAM, giảm kích thước batch/số tiến trình trước. Không tự nâng size vì sẽ thay đổi chi phí dùng credit.

## 11. Quy ước bật, tắt và chạy thí nghiệm

Người quản lý chạy các lệnh sau **trên Windows của mình**, tại thư mục dự án:

```powershell
cd D:\UIT\HK4\KLTN_Draft

# Kiểm tra máy
.\azure\Manage-KltnVm.ps1 -Action Status

# Bật máy
.\azure\Manage-KltnVm.ps1 -Action Start

# Kết nối bằng tài khoản quản lý
.\azure\Manage-KltnVm.ps1 -Action Connect

# Tắt và giải phóng CPU/RAM sau khi cả hai kết thúc
.\azure\Manage-KltnVm.ps1 -Action Stop
```

Trước khi tắt:

1. Xác nhận người còn lại không còn phiên làm việc hoặc thí nghiệm đang chạy.
2. Lưu code, commit/push thay đổi cần thiết và lưu log/checkpoint.
3. Người quản lý chạy `Stop` rồi kiểm tra trạng thái `VM deallocated` hoặc `Stopped (deallocated)`.

Lịch tự tắt **23:00** áp dụng cho cả hai. Phiên SSH đang mở hoặc tác vụ chạy trong nền không ngăn được lịch tắt. Muốn chạy qua đêm, phải điều chỉnh lịch trước và khôi phục sau khi xong.

Đóng cửa sổ SSH không đồng nghĩa tắt VM. Ngược lại, lệnh `shutdown` trong Ubuntu chưa bảo đảm giải phóng tài nguyên tính phí; dùng `Stop` của script hoặc Stop trên Azure và kiểm tra trạng thái deallocated. Ổ đĩa và IP vẫn có thể tính phí khi máy đã tắt.

Đối với tác vụ cần chạy sau khi đóng SSH, có thể dùng `tmux` nếu người quản lý đã cài:

```bash
tmux new -s kltn-run
# Chạy thí nghiệm trong phiên này.
# Để tách phiên: nhấn Ctrl+B, thả ra, rồi nhấn D.
```

Kết nối lại bằng `tmux attach -t kltn-run`. `tmux` giữ phiên khi mất SSH, nhưng không giữ tác vụ sống khi VM bị tắt.

## 12. Xử lý lỗi thường gặp

| Hiện tượng | Kiểm tra và xử lý |
| --- | --- |
| `Connection timed out` | VM đã bật chưa; IP mạng người dùng có đổi không; quy tắc riêng có đủ IP HTTP/HTTPS và cổng 22 không |
| `Permission denied (publickey)` | Đúng username chưa; đúng khóa riêng chưa; public key có nằm trong `authorized_keys` của đúng tài khoản không |
| SSH hỏi mật khẩu Ubuntu | Không nhập mật khẩu Microsoft; kiểm tra khóa và username, không bật password login để chữa tạm |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Dừng, xác minh VM/IP và host fingerprint qua người quản lý trước khi cập nhật known_hosts |
| Không ghi được thư mục người khác | Làm việc trong `~/kltn`; không dùng `chmod 777` để mở quyền toàn bộ thư mục |
| Không chạy được Docker | Tài khoản thường chưa có quyền Docker; nhờ người quản lý chạy hoặc chuẩn bị môi trường phù hợp |
| VM chậm hoặc tiến trình bị kill | Xem RAM, giảm batch/parallelism, tránh chạy hai tác vụ nặng cùng lúc |
| Không chạy được script quản lý trên máy người thứ hai | Script phụ thuộc môi trường Azure CLI và đăng nhập quản trị trên máy chủ tài khoản; người thứ hai chỉ cần SSH |
| Sau triển khai lại template, người thứ hai mất SSH | Kiểm tra quy tắc riêng có bị ghi đè không; bổ sung vào template trước khi triển khai lại |

## 13. Checklist hoàn tất thiết lập

- [ ] Hai máy giữ hai khóa SSH riêng; chỉ trao đổi khóa công khai.
- [ ] Tài khoản `nhu` đã được tạo trên Ubuntu và có đúng public key.
- [ ] Fingerprint public key được đối chiếu giữa hai người.
- [ ] Có quy tắc `AllowSshNhu` riêng, giới hạn địa chỉ `/32` và cổng 22.
- [ ] Người thứ hai đối chiếu host fingerprint và SSH thành công bằng tài khoản `nhu`.
- [ ] Mỗi người có thư mục clone và venv riêng.
- [ ] Hai người thống nhất giờ chạy thí nghiệm, quy trình bật/tắt và lịch 23:00.
- [ ] Không chia sẻ phiên đăng nhập Azure, mật khẩu Microsoft hoặc API key qua file hướng dẫn.

## 14. Phân biệt hướng dẫn và trạng thái đã có

Đã có: VM, tài khoản quản lý `azureuser`, công cụ nền, khóa quản lý trên máy ban đầu và quy tắc IP của người quản lý.

Cần thực hiện theo tài liệu: người thứ hai tạo khóa, gửi `.pub`/IP; người quản lý tạo tài khoản, cấp khóa và thêm quy tắc mạng riêng. Tạo file hướng dẫn này không tự thay đổi quyền truy cập hoặc cấu hình đang chạy trên Azure.
