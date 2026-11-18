# Ghi chú đọc: SocketAI

## Thông tin bài

- Nusrat Zahan, Philipp Burckhardt, Mikola Lysenko, Feross Aboukhadijeh và Laurie Williams, “Leveraging Large Language Models to Detect npm Malicious Packages.”
- Bản preprint đầu tiên: arXiv:2403.12196, đăng ngày 18/03/2024. Bản hội nghị xuất bản tại *2025 IEEE/ACM 47th International Conference on Software Engineering (ICSE 2025)*.
- DOI bản hội nghị: [10.1109/ICSE55347.2025.00146](https://doi.org/10.1109/ICSE55347.2025.00146).
- Toàn văn: [arXiv v4](https://arxiv.org/abs/2403.12196v4).

## Bài toán và đóng góp

SocketAI là workflow dùng LLM để hỗ trợ chuyên gia rà soát mã nguồn package npm độc hại. Bài đánh giá GPT-3.5 và GPT-4 so với 39 rule CodeQL, đo thêm tác dụng của CodeQL khi dùng làm bộ lọc trước LLM và phân tích định tính những loại hành vi mà mô hình bắt được hoặc bỏ sót.

Tên “GPT-3” trong bài là `gpt-3.5-turbo-1106`; “GPT-4” là `gpt-4-1106-preview`. Đây là các model cụ thể của thí nghiệm 2024, không đại diện cho hiệu năng hoặc chi phí model hiện tại.

## Workflow

SocketAI kết hợp zero-shot role-play/chain-of-thought prompting, iterative self-refinement và LLM-as-a-judge:

1. **Initial reports:** mỗi file được phân tích nhiều lần để lấy các báo cáo khác nhau; paper tạo 5 báo cáo GPT-3 và 3 báo cáo GPT-4 cho mỗi file.
2. **Critical reports:** mô hình rà soát các báo cáo ban đầu, xác minh evidence trong mã và chất vấn kết luận/risk score.
3. **Final report:** mô hình chọn hoặc viết lại báo cáo cuối, nêu purpose, source, sink, data flow, phân tích, mức tin cậy và các score.
4. **Human review:** chuyên gia xem báo cáo cuối; file có malware score trên 0,5 được ưu tiên triage.

Đầu ra theo JSON, nhưng nhóm tác giả ghi nhận vẫn có lỗi schema, thiếu/thừa key, JSON sai cú pháp hoặc bị cắt; họ phải dùng parser dung sai để xử lý.

## Dữ liệu và thiết kế đánh giá

MalwareBench trong nghiên cứu có 5.115 package: 2.180 package chứa mã độc và 2.935 package neutral. Bộ mẫu thực nghiệm tương ứng 2.776 phiên bản độc hại và 2.974 phiên bản neutral, tổng cộng 20.926 file (18.754 file duy nhất). Vì giới hạn chi phí, tác giả lấy mẫu phân tầng ưu tiên package nhỏ hơn; package rất lớn bị loại khỏi một phần đánh giá.

CodeQL dùng 39 query tùy chỉnh được xây từ nghiên cứu trước. Bài lưu ý recall CodeQL cao có thể do các query được phát triển từ cùng tập mẫu malware liên quan; đây là điểm cần cân nhắc khi đọc so sánh baseline.

## Kết quả chính

| Phương pháp | Precision | Recall | F1 | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| CodeQL | 0,75 | 0,97 | 0,85 | 684 | 60 |
| GPT-3.5 (`gpt-3.5-turbo-1106`) | 0,91 | 0,97 | 0,94 | 195 | 52 |
| GPT-4 (`gpt-4-1106-preview`) | 0,99 | 0,95 | 0,97 | 3 | 90 |

- GPT-4 đạt precision/F1 cao nhất và ít false positive nhất trong benchmark; GPT-3.5 có recall cao hơn trong bảng kết quả. GPT-4 có 90 false negative so với 52 của GPT-3.5, vì vậy precision cao không đồng nghĩa không bỏ sót mẫu.
- Hai model cùng phát hiện 2.057 trong 2.180 package độc hại; GPT-3.5 phát hiện 2.128, GPT-4 phát hiện 2.089.
- CodeQL đánh dấu 4.146 trong 18.754 file duy nhất. Dùng CodeQL làm pre-screener giảm 77,9% số file đưa qua LLM.
- Trên chi phí thí nghiệm được báo cáo, quét đủ file tốn $125,65 với GPT-3.5 và $2.013,84 với GPT-4; chỉ quét file CodeQL đã chọn tốn lần lượt $49,13 và $482,46. Đây là giá lịch sử của model/API trong thí nghiệm, không dùng làm dự toán hiện tại.
- Phân tích định tính thường gặp data theft/exfiltration, thực thi lệnh tùy ý, domain đáng ngờ, reverse shell, backdoor, typosquatting và dependency confusion. Các nhóm có thể chồng lấp.

## Khó khăn và giới hạn

- **Mode collapse/hallucination:** các lần tạo báo cáo có thể lặp lại cùng nhận định sai thay vì mang lại góc nhìn độc lập.
- **Giới hạn ngữ cảnh:** file lớn và luồng dữ liệu qua nhiều file/module khó phân tích; chia file để vừa context cũng có thể làm mất ngữ cảnh.
- **Prompt injection:** bộ dữ liệu không có tập kiểm thử prompt injection được thiết kế hệ thống; một ví dụ đơn lẻ không đủ chứng minh khả năng chống chịu.
- **Chất lượng nhãn:** MalwareBench có thể thiên lệch theo loại malware; nhóm xây dataset chỉ kiểm tra thủ công một phần package neutral. Nhóm SocketAI tự kiểm tra 2.530 trong 20.926 file, nhưng không loại trừ hoàn toàn malware chưa phát hiện.
- **Selection bias:** giới hạn chi phí khiến mẫu ưu tiên package nhỏ; kết quả có thể không đại diện cho package lớn hoặc mã độc phức tạp hơn.
- **Phạm vi:** chỉ nghiên cứu npm và hai đời GPT cụ thể; không suy rộng trực tiếp sang PyPI, model khác hay giá API hiện tại.
- **Baseline:** 39 CodeQL rules có độ phủ cao trên cùng loại tập malware dùng trong quá trình phát triển rule, nên lợi thế recall của CodeQL có thể bị ảnh hưởng bởi sự tương đồng dữ liệu.

## Liên hệ với khóa luận

1. SocketAI là workflow có nhiều lượt LLM và bước người đánh giá, không phải một prompt phân loại package đơn giản. So sánh chi phí cần tính số lượt, số file, token và thời gian triage.
2. Có thể dùng static analysis để thu hẹp file cần LLM đọc, nhưng cần đo riêng coverage/false negative do bộ lọc loại file trước.
3. Giữ evidence ở cấp file và phân biệt package label với file finding; tránh kết luận toàn package từ một đoạn mã thiếu ngữ cảnh.
4. Cố định model/version, prompt, số lượt, ngưỡng score và rule snapshot trước khi chạy test; bổ sung kiểm tra JSON/schema, prompt injection, file lớn và malware phân tán qua nhiều file.
5. Dùng cùng manifest và ground truth độc lập cho CodeQL/GuardDog, ML, LLM và hybrid. Kết quả này không chứng minh GPT-4 hiện tại sẽ giữ nguyên mức 99% precision/97% F1.

## Tài liệu tham khảo

- Zahan, N. et al. (2025). *Leveraging Large Language Models to Detect npm Malicious Packages*. ICSE 2025. https://doi.org/10.1109/ICSE55347.2025.00146
- Bản preprint đăng năm 2024: https://arxiv.org/abs/2403.12196v4
