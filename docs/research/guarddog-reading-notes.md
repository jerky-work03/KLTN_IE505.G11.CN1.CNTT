# Ghi chú đọc: GuardDog

## Nguồn đã đọc

1. Wang, E. và Tafani-Dereeper, C., “Finding malicious PyPI packages through static code analysis: Meet GuardDog,” Datadog Security Labs, 2022-11-15. Đây là bài chính thức giới thiệu GuardDog.
2. Guo et al., “How Effective Are NPM Malicious Package Detectors? A Large-Scale Empirical Study,” arXiv:2603.27549v2, 2026. Bài nghiên cứu đánh giá GuardDog trong nhóm công cụ phát hiện package npm độc hại.
3. Tài liệu chính thức [DataDog/GuardDog](https://github.com/DataDog/guarddog/tree/v3), nhánh v3, dùng để xác minh cách công cụ hiện tại hoạt động và phạm vi hỗ trợ.

## GuardDog là gì?

GuardDog là công cụ CLI phân tích package tĩnh, không cần cài hay gọi mã package đích. Có thể quét package từ registry hoặc archive cục bộ; bản hiện hành hỗ trợ npm, PyPI cùng một số hệ sinh thái khác.

Ở phiên bản được bài blog giới thiệu năm 2022, rule mã nguồn dùng Semgrep, gồm taint tracking để theo dõi dữ liệu nhạy cảm đến điểm gửi mạng/thực thi; metadata rule kiểm tra typosquatting, email maintainer và thông tin package. Ví dụ heuristic: thực thi dữ liệu Base64, tải rồi chạy executable, exfiltrate biến môi trường, domain đáng ngờ, ghi đè install command, tên gần với package phổ biến.

GuardDog v3 hiện dùng rule YARA cho mã nguồn và metadata heuristic. Tài liệu v3 mô tả các bước: phát hiện capability và threat indicator, tương quan chúng (cùng file tạo risk; khác file có thể giảm severity), rồi tính risk score 0–10. Vì vậy không nên mô tả Semgrep là kiến trúc hiện tại của mọi phiên bản GuardDog.

Một finding về **khả năng** (ví dụ đọc file, gọi mạng hoặc tạo process) khác với **threat indicator**. API nhạy cảm có thể xuất hiện trong chức năng hợp lệ; capability đơn lẻ không tự chứng minh ý đồ độc hại. Đây cũng là lý do điểm risk có thể bằng 0 dù output còn capability findings.

## Ghi chú bài Datadog 2022

- Bài giải thích supply-chain risk qua các giai đoạn: kẻ tấn công đưa package vào registry, package thực thi trong lúc cài/import, rồi lấy cắp dữ liệu hoặc tải payload tiếp theo.
- Tác giả xây heuristics từ phân tích ngược các package PyPI độc hại đã biết. Cách tiếp cận dựa trên hành vi phổ biến, không phải danh sách hash/signature của từng mẫu; mục tiêu là phát hiện cả package chưa từng thấy nếu chúng có hành vi phù hợp rule.
- Rule mã nguồn tiêu biểu: lệnh cài đặt bị ghi đè trong `setup.py`, thực thi nội dung Base64/ẩn trong ảnh, tải executable rồi chạy, gửi thông tin nhạy cảm ra mạng, và truy cập domain có đuôi đáng ngờ hoặc dịch vụ rút gọn URL.
- Rule metadata tiêu biểu: phát hiện tên package gần với top 5.000 package phổ biến, domain email maintainer có dấu hiệu đăng ký lại, mô tả thiếu hoặc phiên bản `0.0.0`.
- CLI hỗ trợ quét package mới nhất, chỉ định version, chọn/bỏ rule, quét archive cục bộ và quét các dependency trong `requirements.txt`.
- Đây là bài giới thiệu kỹ thuật, không phải benchmark độc lập. Bài không đưa ra precision/recall/F1 đủ để kết luận hiệu năng; các heuristic được hình thành từ tập hành vi mà nhóm tác giả đã quan sát nên có thể bỏ sót hành vi mới hoặc bị biến đổi. Đây là giới hạn suy ra từ cách xây heuristic, không phải số đo false negative được bài báo cáo.

## Bài nghiên cứu

Bài arXiv xây dựng benchmark npm gồm 6.420 phiên bản package độc hại và 7.288 package lành tính, gắn taxonomy 11 nhóm hành vi và 8 kỹ thuật né tránh, rồi đánh giá 11 công cụ với 16 biến thể. Thí nghiệm dùng cấu hình mặc định của công cụ để ưu tiên khả năng tái lập và phản ánh cách dùng thông thường. Nhóm tác giả cũng đọc mã nguồn detector nhằm giải thích vì sao chúng bắt được hoặc bỏ sót mẫu.

Kết quả liên quan trực tiếp đến GuardDog:

- GuardDog đạt F1 93,32%, cao nhất trong nhóm công cụ conventional được so sánh. IntelGuard đạt F1 95,98% khi dùng bằng chứng truy xuất. Đây là kết quả trên tập npm và cấu hình của nghiên cứu, không phải cam kết hiệu năng chung.
- Một nguyên nhân nền tảng là sự nhập nhằng giữa khả năng và ý đồ: API đọc file hoặc gửi request có thể dùng hợp lệ. Chuỗi hành vi có ngữ cảnh như thu thập thông tin, tuần tự hóa rồi gửi ra ngoài thường thể hiện ý đồ rõ hơn một API đơn lẻ.
- Bài báo cho biết 80,3% mẫu malware không dùng kỹ thuật né tránh; việc thiếu quét bắt buộc trước khi phát hành được nêu như một nguyên nhân hệ thống.
- Tổ hợp nhiều detector không tự động tốt hơn. Giá trị phụ thuộc vào phần phát hiện bổ sung trừ đi false positive mới; một detector nhiều false positive có thể làm giảm chất lượng của detector khác.
- Tổ hợp chiến lược đạt tối đa 97,21% accuracy và 97,02% F1 trong benchmark của bài.

## Giới hạn cần giữ khi áp dụng

- Bài đánh giá npm; không suy rộng trực tiếp kết quả sang PyPI. Dự án cần báo cáo hai hệ sinh thái riêng.
- Benchmark tập trung mạnh vào package giai đoạn 2021–2025. Kết quả phụ thuộc snapshot, nguồn dữ liệu, nhãn và phiên bản rule.
- Nhóm nghiên cứu dùng cấu hình mặc định. Đổi phiên bản GuardDog, rule hoặc cách quy đổi finding thành prediction sẽ tạo điều kiện đánh giá khác.
- Tác giả báo cáo đồng thuận nhãn chuyên gia 97,4%, nhưng vẫn nêu nguy cơ nhãn biên bị phân loại sai và giới hạn về khả năng khái quát.
- Dataset có nguồn Datadog; không dùng kết quả GuardDog để tự tạo nhãn rồi dùng chính nhãn đó chứng minh GuardDog hiệu quả. Cần xem xét selection bias và nguồn độc lập.

## Áp dụng cho khóa luận

1. Ghi lại phiên bản GuardDog, snapshot rule, metadata nguồn, tùy chọn sandbox và quyết định quy đổi finding trước khi chạy tập đánh giá chính.
2. Giữ riêng capability finding và threat finding trong evidence. Không chuyển một capability finding đơn lẻ thành nhãn `malicious`.
3. Dùng cùng manifest mẫu cho GuardDog, ML, LLM và hybrid; phân tầng metric theo npm/PyPI, rule coverage và trạng thái `inconclusive`/`error`.
4. Xem lần quét `requests` và `express` ngày 2026-11-17 là smoke check giao diện công cụ, không phải benchmark: hai package chưa có nhãn ground truth trong run đó.

## Tài liệu tham khảo

- Guo, W. et al. (2026). *How Effective Are NPM Malicious Package Detectors? A Large-Scale Empirical Study*. arXiv:2603.27549v2. https://arxiv.org/abs/2603.27549v2
- Wang, E. & Tafani-Dereeper, C. (2022-11-15). *Finding malicious PyPI packages through static code analysis: Meet GuardDog*. Datadog Security Labs. https://securitylabs.datadoghq.com/articles/guarddog-identify-malicious-pypi-packages/
- DataDog. *GuardDog: CLI tool to identify malicious packages*. https://github.com/DataDog/guarddog/tree/v3
