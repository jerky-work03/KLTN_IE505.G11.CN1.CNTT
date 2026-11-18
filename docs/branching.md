# Quy trình nhánh Git

```text
main                        Bản ổn định
└── dev                     Tích hợp thay đổi
    ├── hieu/<task>         Công việc của Hiếu
    ├── nhu/<task>          Công việc của Nhu
    └── shared/<task>       Công việc chung
```

Đây là phân cấp theo quy trình. Git lưu quan hệ giữa commit, không lưu thuộc tính parent/child của nhánh. `feature/*` là cách gọi nhóm nhánh công việc; dự án giữ quy ước `<nguoi>/<task>` hiện có.

| Nhánh | Tạo từ | PR vào | Vai trò |
|---|---|---|---|
| `main` | Đã có | — | Bản ổn định, nhận bản phát hành từ `dev` |
| `dev` | Đã có | `main` | Tích hợp các task đã review |
| `hieu/<task>` | `origin/dev` | `dev` | Task của Hiếu |
| `nhu/<task>` | `origin/dev` | `dev` | Task của Nhu |
| `shared/<task>` | `origin/dev` | `dev` | Task chung |

## Tạo nhánh công việc

```powershell
git fetch origin
git switch dev
git pull --ff-only origin dev
git switch -c hieu/W05-hybrid-routing
```

Thay tên ví dụ bằng task cần làm. Nếu chưa có `dev` local, dùng `git switch --track origin/dev` cho lần đầu.

## Cập nhật và gửi task

Commit hoặc lưu thay đổi đang làm trước khi cập nhật nhánh. Với nhánh dùng chung hoặc đã push, merge từ `dev` để giữ lịch sử:

```powershell
git fetch origin
git merge origin/dev
python -m pytest -q
python -m ruff check src tests
git diff --check
git status --short
```

Nếu có conflict, xử lý theo mục 8 của `TEAM_RULES.md`; không tự chọn một phía. Chỉ commit những file thuộc task, không thêm secret, `.env` hay `workspace-support/`.

Push nhánh công việc và mở PR với **base: `dev`**, **compare: nhánh công việc**. Không mở PR task trực tiếp vào `main`.

## Phát hành

Sau khi các task đã được review, merge vào `dev` và kiểm tra xong, mở PR với **base: `main`**, **compare: `dev`**. Không commit trực tiếp lên `main`.

## Nhánh hiện có và lịch sử revert

Giữ nguyên các nhánh `hieu/W01-guarddog-reading`, `ngo-thi-duc-nhu`, `nguyen-trung-hieu` và `nhu/W02-benign-npm`; không đổi tên, xóa, rebase hoặc force-push để dựng lại cây lịch sử. Công việc mới luôn tạo từ `dev` mới nhất. Các nhánh cũ dùng làm tham chiếu lịch sử.

`main` có revert commit `7e9407d` hoàn tác merge `09b41d9`. Revert giữ các commit đã merge trong lịch sử; merge lại nhánh cũ không tự khôi phục nội dung bị hoàn tác. Trước PR phát hành tiếp theo, phải kiểm tra diff và xử lý việc khôi phục nội dung cần thiết trên một nhánh công việc riêng qua `dev`.

Quy trình này được ghi trong tài liệu; chưa cấu hình GitHub branch protection hay ruleset để bắt buộc thực thi. Không thay đổi các thiết lập đó khi chưa thống nhất cả hai thành viên theo `TEAM_RULES.md`.
