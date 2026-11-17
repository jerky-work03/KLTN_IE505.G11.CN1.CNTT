# Ghi chú đọc: Amalfi (ICSE 2022)

## Thông tin bài

- Adriana Sejfia và Max Schäfer, “Practical Automated Detection of Malicious npm Packages,” *Proceedings of the 44th International Conference on Software Engineering (ICSE 2022)*, trang 1681–1692.
- DOI: [10.1145/3510003.3510104](https://doi.org/10.1145/3510003.3510104).
- Bản open access: [arXiv:2202.13953](https://arxiv.org/abs/2202.13953).
- Artifact bổ sung mà bài báo dẫn: [githubnext/amalfi-artifact](https://github.com/githubnext/amalfi-artifact) và [Zenodo 5908852](https://doi.org/10.5281/zenodo.5908852).

## Bài toán và ý tưởng

NPM xuất bản số lượng lớn phiên bản package, khiến việc kiểm tra thủ công mọi bản phát hành không khả thi. Amalfi hướng tới phát hiện sớm phiên bản có khả năng độc hại để con người triage và báo cho npm. Ý tưởng trung tâm là kết hợp thay đổi hành vi giữa các phiên bản với thông tin nguồn package, thay vì xem một API nhạy cảm đơn lẻ là bằng chứng đủ.

Amalfi gồm ba thành phần bổ trợ nhau:

1. **Classifier:** học từ package độc hại/lành tính đã gán nhãn, dùng đặc trưng package và thay đổi so với phiên bản trước.
2. **Reproducer:** khi classifier báo động và package có source repository, thử build lại package từ source rồi so sánh với tarball trên registry. Nếu tái tạo được thì dùng làm tín hiệu lọc false positive, không phải bằng chứng chắc chắn lành tính. Tỷ lệ tái tạo thành công trong thực tế thấp.
3. **Clone detector:** so hash nội dung package với các mẫu độc hại đã biết; bỏ `name` và `version` khỏi `package.json` trước khi hash để bắt bản sao đổi tên/phiên bản. Cách này chủ yếu bắt clone gần như nguyên bản, không phải biến thể đã sửa mã.

## Đặc trưng và mô hình

Bài xác định 11 loại đặc trưng: chín đặc trưng ở cấp một phiên bản và hai đặc trưng theo thời gian. Nhóm một phiên bản gồm truy cập PII (password, cookie, dữ liệu thẻ), truy cập filesystem/process/network, API crypto, encoding, dynamic code generation, install scripts, và dấu hiệu mã minify/binary. Hai đặc trưng theo thời gian là thời gian giữa các lần phát hành và loại cập nhật semver. Mô hình còn dùng mức thay đổi của các đặc trưng một phiên bản giữa hai bản liên tiếp.

JavaScript/TypeScript được phân tích cú pháp bằng Tree-sitter AST; `package.json` được kiểm tra để phát hiện lifecycle scripts. Shannon entropy của file dùng làm tín hiệu cho minified/binary. Timestamp npm và semver cung cấp đặc trưng thời gian/cập nhật.

Do corpus nhỏ và lệch lớp, nhóm thử ba mô hình: decision tree, Bernoulli Naive Bayes và one-class linear SVM (SVM chỉ học trên mẫu lành tính). Corpus cơ bản gồm 643 phiên bản độc hại npm do npm cung cấp và 1.147 phiên bản lành tính của các package tương ứng, tổng cộng 1.790 mẫu; tập này cố ý oversample mẫu độc hại so với tỷ lệ ngoài thực tế.

## Thiết kế và kết quả

- **Quét phát hành mới:** quét toàn bộ phiên bản public mới trong một tuần, 29/07–04/08/2021, tổng cộng 96.287 phiên bản. Mỗi ngày, tác giả triage các cảnh báo, báo mẫu độc hại đã xác minh cho npm rồi cập nhật tập huấn luyện cho ngày sau.
- Sau khi gộp phần trùng giữa classifier, Amalfi tìm 95 mẫu độc hại chưa được biết trước trong tuần đó. Các mẫu được báo npm và sau đó bị gỡ khỏi registry.
- Ngày đầu tạo quá nhiều cảnh báo, nên tác giả chỉ kiểm tra chi tiết một phần; họ tạm coi package không bị báo là lành tính để huấn luyện các ngày kế tiếp. Số false positive của ngày đầu vì thế có thể bị phóng đại, còn giả định nhãn cho phần không kiểm tra có thể làm tăng false negative về sau.
- **Đánh giá nhãn:** 10-fold cross-validation trên corpus cơ bản cho decision tree precision 0,98 / recall 0,43; Naive Bayes 0,90 / 0,19; one-class SVM 0,98 / 0,27. Kết quả SVM được đặt trong ngoặc trong bài vì tham số `nu` được chọn trên cùng corpus.
- Trên tập MalOSS sau khi loại overlap (372 phiên bản, gồm 40 mẫu độc hại), precision/recall lần lượt là decision tree 0,35/0,64, Naive Bayes 0,62/0,64, SVM 0,73/0,61. Tác giả lưu ý một số nhãn độc hại trong MalOSS không được npm xác nhận.
- Huấn luyện và dự đoán đều nhanh; phần lớn package được trích đặc trưng trong dưới một giây, nhưng có một package hơn 11.000 file mất trên 10 phút. Dự đoán từng package dưới một giây.

## Nhận xét và giới hạn

- Kết quả 95 mẫu mới là kết quả của một tuần quét có người triage và incremental retraining, không phải recall trên toàn bộ ground truth đã biết.
- Recall của các classifier trên corpus cơ bản thấp (0,19–0,43); precision cao không đồng nghĩa bỏ sót ít malware. Clone detector bổ sung exact copies nhưng không thay cho phát hiện biến thể.
- Dữ liệu ban đầu chỉ có 643 mẫu độc hại và oversample malware. Kết quả phụ thuộc thời kỳ, registry và cách chọn benign/malicious; không suy rộng sang PyPI.
- Pipeline reproducer gặp khó vì source repo, commit, build command và toolchain thường thiếu hoặc không cố định. Không tái tạo được package không tự nó chứng minh package độc hại.
- Tác giả nêu nguy cơ dataset có cụm package tương tự do các chiến dịch copycat, giới hạn năm phút kiểm tra mỗi cảnh báo, khả năng gán nhãn sai, và giả định các package không bị flag là benign.
- So với GuardDog, Amalfi là hướng ML dựa trên đặc trưng và lịch sử package, có thêm reproducibility check và clone matching; GuardDog là detector theo rule/heuristic. Đây là khác biệt thiết kế, không phải so sánh hiệu năng trực tiếp từ paper này.

## Liên hệ với khóa luận

1. Lưu version history, thời gian phát hành, loại semver update và thay đổi feature nếu muốn tái hiện hướng Amalfi; snapshot một bản package sẽ bỏ mất tín hiệu thời gian cốt lõi.
2. Đánh giá precision và recall riêng, xử lý imbalance, và không gán benign tự động cho toàn bộ mẫu không bị cảnh báo.
3. Giữ reproducer như tín hiệu bổ trợ. Nếu sử dụng build step, chạy trong môi trường cô lập; không cài hoặc thực thi package nghiên cứu trên host.
4. Khi so sánh với GuardDog, dùng cùng manifest và nhãn ground truth độc lập; không dùng output của một detector để tạo nhãn chuẩn cho chính detector đó.

## Tài liệu tham khảo

- Sejfia, A. & Schäfer, M. (2022). *Practical Automated Detection of Malicious npm Packages*. ICSE 2022, 1681–1692. https://doi.org/10.1145/3510003.3510104
- Bản preprint: https://arxiv.org/abs/2202.13953
