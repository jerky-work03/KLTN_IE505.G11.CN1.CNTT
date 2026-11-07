# Kế hoạch thực hiện khóa luận tốt nghiệp

**Đề tài:** Nghiên cứu phương pháp phát hiện gói thư viện độc hại trên npm và PyPI kết hợp học máy và mô hình ngôn ngữ lớn.

**Thời gian:** 05/11/2026–17/01/2027, gồm 74 ngày, chia thành 11 tuần kế hoạch; tuần cuối có 4 ngày.

**Người thực hiện:** Ngô Thị Đức Nhu và Nguyễn Trung Hiếu.

**Giảng viên hướng dẫn:** ThS. Nghi Hoàng Khoa.

Kế hoạch tập trung vào một thực nghiệm có thể tái lập: so sánh GuardDog, Random Forest, XGBoost, LLM và pipeline kết hợp trên dữ liệu npm/PyPI. Kết quả chính là đo khả năng phát hiện, số lần gọi LLM, chi phí và thời gian. Prototype CLI phục vụ chạy thực nghiệm và minh họa ứng dụng.

Phân công dưới đây là đề xuất theo hướng đã nêu trong đề cương: Nhu phụ trách dữ liệu, đặc trưng và ML; Hiếu phụ trách GuardDog, LLM, hybrid và CLI. Hai thành viên cùng quyết định giao thức thực nghiệm, kiểm tra dữ liệu, đánh giá và hoàn thiện báo cáo.

## 1. Mục tiêu và câu hỏi nghiên cứu

| Mã | Câu hỏi nghiên cứu | Bằng chứng cần tạo |
| --- | --- | --- |
| RQ1 | GuardDog, RF, XGBoost và LLM phát hiện gói độc hại hiệu quả đến đâu trên cùng tập đánh giá? | Precision, Recall, F1, FPR, confusion matrix và tỷ lệ không phân tích được; tách riêng npm/PyPI |
| RQ2 | Zero-shot, few-shot và prompt kèm bằng chứng tĩnh khác nhau thế nào? | Kết quả validation, token, latency, chi phí và ví dụ giải thích |
| RQ3 | Hybrid giảm được bao nhiêu lượt gọi LLM và chi phí khi giới hạn mức suy giảm recall? | Đường đánh đổi ngưỡng ML, recall toàn pipeline, tỷ lệ chuyển LLM, chi phí và thời gian |
| RQ4 | Obfuscation và prompt injection làm suy giảm kết quả đến mức nào? | Kết quả trước/sau trên cùng mẫu, tỷ lệ né phát hiện và phân tích lỗi |
| RQ5 | Giải thích của LLM có đúng với bằng chứng trong gói không? | Đánh giá thủ công theo tiêu chí thống nhất và các trường hợp giải thích sai |

**Giả thuyết chính:** một ngưỡng sàng lọc ML phù hợp có thể giảm số lượt gọi LLM trong khi duy trì recall gần với LLM độc lập. Đây là giả thuyết cần kiểm chứng. Kết quả không cải thiện hoặc chỉ cải thiện trong một số điều kiện vẫn phải được báo cáo.

## 2. Phạm vi và đầu ra bắt buộc

### 2.1. Phạm vi nghiên cứu

- Hai hệ sinh thái: npm và PyPI.
- Phân tích tĩnh archive `.tgz`, `.tar.gz`, `.whl`; không thực thi mã nguồn hoặc script cài đặt của mẫu.
- Nhãn đánh giá ở mức gói và phiên bản: độc hại hoặc lành tính theo tiêu chí gán nhãn đã công bố.
- RF và XGBoost dùng đặc trưng tĩnh và metadata; không huấn luyện LLM từ đầu.
- Chọn một LLM chính. So sánh ba chiến lược prompt trên validation, sau đó cố định cấu hình để đánh giá test.
- Thử nghiệm chống chịu có tập mẫu và phép biến đổi được giới hạn trước.

### 2.2. Đầu ra bắt buộc

1. Manifest dữ liệu có nguồn, phiên bản, nhãn, mốc thời gian và hash; script làm sạch, chia tập và thống kê.
2. Bộ trích xuất đặc trưng cho npm/PyPI, tài liệu schema và kiểm thử các trường hợp quan trọng.
3. GuardDog baseline, RF, XGBoost, LLM baseline và hybrid chạy được bằng cấu hình lưu trong repo.
4. Bảng so sánh trên cùng tập test, kết quả riêng theo hệ sinh thái, phân tích FP/FN, chi phí và thời gian.
5. Báo cáo thử nghiệm obfuscation, prompt injection và đánh giá giải thích.
6. CLI quét archive trực tiếp và chế độ dependency giới hạn được mô tả bên dưới.
7. Báo cáo khóa luận, slide, script demo, README và gói kết quả tái lập.

### 2.3. Phạm vi CLI để thống nhất với đề cương

Chức năng đọc `package-lock.json` và `requirements.txt` là **đầu ra bắt buộc ở phạm vi giới hạn**, không để thành công việc tùy chọn.

| Đầu vào | Phạm vi hỗ trợ bắt buộc | Cách xử lý ngoài phạm vi |
| --- | --- | --- |
| Archive | Nhận đường dẫn archive npm/PyPI; phân tích tĩnh và xuất JSON | Báo lỗi rõ khi archive hỏng, quá lớn hoặc định dạng không hỗ trợ |
| `package-lock.json` | Một phiên bản lockfile được chọn và ghi rõ sau khảo sát tuần 1; quét các mục npm registry có tên và phiên bản xác định | Ghi trạng thái `unsupported` cho Git, đường dẫn cục bộ hoặc mục không xác định được archive |
| `requirements.txt` | Dòng package từ PyPI có phiên bản cố định dạng `name==version` | Ghi `unsupported` cho khoảng phiên bản, Git, đường dẫn cục bộ và cú pháp chưa hỗ trợ |

Với PyPI, phải ghi lại archive cụ thể đã chọn và hash vì một phiên bản có thể có nhiều wheel/sdist. `requirements.txt` chỉ được hiểu là danh sách khai báo; CLI không tuyên bố đã quét đầy đủ dependency bắc cầu.

CLI không chạy `npm install`, `pip install`, build wheel hoặc resolve dependency bằng cách thực thi mã gói. Kết quả cần phân biệt `malicious`, `benign`, `inconclusive`, `error`, `unsupported`; không đổi lỗi phân tích thành kết luận lành tính.

## 3. Giao thức dữ liệu và thực nghiệm

### 3.1. Thu thập và gán nhãn

- Chốt commit/snapshot của Datadog và OpenSSF dùng trong nghiên cứu.
- Thống kê riêng số archive npm/PyPI có thể sử dụng. Không lấy tổng số mẫu của toàn repository làm số mẫu npm/PyPI.
- Phân biệt package có trong manifest với package thực sự có archive tải được.
- Lưu tối thiểu: `sample_id`, ecosystem, package, version, artifact filename, SHA-256, nguồn, nhãn, căn cứ nhãn, ngày phát hành, ngày phát hiện, ngày thu thập và trạng thái xử lý.
- Không dùng ngày trong tên archive Datadog thay cho ngày phát hành nếu chưa xác minh. Mẫu thiếu ngày phát hành được thống kê riêng và xử lý theo quy tắc đã chốt trước khi chia tập.
- Gói lành tính phải có tiêu chí chọn mẫu rõ; lấy cả gói phổ biến và ít phổ biến. Việc không có trong danh sách mã độc không đủ để khẳng định lành tính.
- Kiểm tra thủ công một tập con của dữ liệu lành tính và ghi nhận các trường hợp chưa chắc chắn. Không dùng GuardDog làm nguồn nhãn duy nhất rồi dùng chính bộ nhãn đó để khẳng định hiệu quả GuardDog.
- Ghi nhận khả năng Datadog và OpenSSF cùng tham chiếu một sự kiện; đối chiếu hai nguồn không mặc nhiên tạo ra bằng chứng độc lập.

**Quy mô khởi đầu đề xuất:** 1.000–2.000 mẫu mỗi hệ sinh thái, có cả hai lớp. Đây là mục tiêu để lập ngân sách, không phải số dữ liệu đã có. Chốt quy mô sau pilot tuần 2 dựa trên khả năng tải mẫu, chất lượng nhãn và tài nguyên.

### 3.2. Loại trùng và chia tập

1. Loại archive trùng hash và phát hiện mã nguồn gần trùng theo phương pháp được ghi rõ.
2. Nhóm các biến thể gần trùng; không để cùng nhóm xuất hiện ở nhiều tập.
3. Chia train/validation/test theo các mốc thời gian phát hành. Chốt mốc sau khi khảo sát phân bố, không ép tỷ lệ nếu làm hỏng tính thời gian hoặc số lượng lớp cần thiết.
4. Với nhóm xuất hiện qua nhiều mốc thời gian, áp dụng một quy tắc nhất quán, chẳng hạn loại nhóm xuyên mốc khỏi đánh giá chính; báo số mẫu bị loại và phân tích ảnh hưởng.
5. Chỉ fit bước tiền xử lý trên train. Chọn siêu tham số, ngưỡng, prompt và few-shot examples bằng train/validation.
6. Khóa danh sách test, hash và nhãn ở cuối tuần 2. Không dùng test để sửa prompt hoặc chọn mô hình.

Không đưa đường dẫn chứa nhãn, cảnh báo có sẵn của nguồn dữ liệu hoặc báo cáo kết luận mã độc vào đặc trưng/prompt. Metadata biến đổi theo thời gian cần có mốc thu thập; nếu không phục hồi được trạng thái lịch sử, phải nêu giới hạn của phép đánh giá theo thời gian.

### 3.3. Các phương pháp và điều kiện so sánh

| Phương pháp | Cấu hình cần cố định | Lưu ý |
| --- | --- | --- |
| GuardDog | Phiên bản, bộ luật, tùy chọn quét, nguồn metadata và quy tắc đổi cảnh báo thành nhãn | Mô tả đúng Semgrep/YARA/metadata theo phiên bản sử dụng |
| RF | Feature schema, preprocessing, seed và siêu tham số | Chọn cấu hình bằng validation |
| XGBoost | Feature schema, preprocessing, seed và siêu tham số | Chọn cấu hình bằng validation |
| LLM | Model/version, prompt, file selector, token budget, temperature và JSON schema | Dữ liệu few-shot lấy từ train; không lấy từ test |
| Hybrid | ML được chọn, ngưỡng, prompt và decision rules | Đánh giá trên toàn luồng, gồm các mẫu bị ML bỏ qua |

- Giữ cùng cơ chế chọn file và giới hạn ngữ cảnh khi so sánh prompt; ghi rõ phần thông tin bổ sung trong prompt có bằng chứng tĩnh.
- Nếu LLM chỉ chạy trên một tập con vì ngân sách, chọn tập con test trước khi xem dự đoán và cho **tất cả phương pháp** chạy trên cùng tập đó. Kết quả ML trên toàn test được trình bày riêng.
- Tập con phải có mẫu thuộc cả hai lớp và cả hai hệ sinh thái. Báo số lượng và cách lấy mẫu.
- Công bố tỷ lệ lớp của tập đánh giá. Precision trên tập cân bằng không được diễn giải trực tiếp thành precision ngoài thực tế.
- Chi phí bao gồm lượt gọi lỗi/retry có tính phí. Thời gian báo riêng chi phí tải dữ liệu và thời gian phân tích; nêu điều kiện cache, phần cứng và mức song song.
- Lưu kết quả từng mẫu để tái tính metrics, khoảng tin cậy và bảng so sánh.

### 3.4. Quy tắc hybrid

- ML trả score; gói có score đạt ngưỡng được chuyển cho LLM.
- Gói dưới ngưỡng được kết luận theo decision rule đã công bố. Nếu mặc định lành tính, mọi mẫu độc hại tại nhánh này phải được tính là false negative.
- LLM lỗi/timeout/JSON không hợp lệ trả `inconclusive` hoặc `error`, kèm giới hạn retry; không tự gán lành tính.
- Báo riêng coverage, số mẫu chưa có kết luận và metrics trên các mẫu có kết luận. Với recall vận hành toàn tập, mẫu độc hại chưa được phát hiện vẫn là mẫu bỏ sót; không loại chúng để làm tăng recall.
- Không dùng `confidence` do LLM tự khai như xác suất đã được hiệu chỉnh.
- Chọn ngưỡng theo mục tiêu recall trên validation và khảo sát số lượt gọi LLM tương ứng. Chốt mức suy giảm recall chấp nhận được trước khi mở kết quả test.
- Nếu không tìm được cấu hình vừa tiết kiệm vừa đạt yêu cầu recall, báo cáo đường đánh đổi và nguyên nhân; không điều chỉnh test để đạt mục tiêu.

### 3.5. Thử nghiệm bổ sung có giới hạn

**Ablation:** tối thiểu so sánh ML có/không có metadata và LLM có/không có bằng chứng tĩnh. Tận dụng các cấu hình đã có để giới hạn chi phí.

**Obfuscation:** chọn trước 2–3 phép biến đổi phù hợp với ngôn ngữ, mô tả căn cứ bảo toàn hành vi và kiểm tra cú pháp khi có thể. So sánh trên các cặp mẫu gốc/biến đổi, không thực thi mẫu. Chỉ báo Precision/FPR nếu tập thử có mẫu lành tính phù hợp; tập chỉ có mã độc dùng recall và tỷ lệ né phát hiện.

**Prompt injection:** đặt chỉ thị gây nhiễu trong các vị trí thực sự được file selector đưa vào ngữ cảnh. Phát triển prompt phòng vệ trên validation; đánh giá cuối trên tập giữ riêng. Tính tỷ lệ tấn công thành công trên các mẫu độc hại vốn được nhận diện đúng rồi bị đổi sang lành tính. Báo thêm lỗi đầu ra và thay đổi giải thích. Với hybrid, ghi rõ mẫu có đi qua tầng LLM hay không.

**Giải thích:** chọn trước tập mẫu để hai thành viên chấm độc lập theo ba tiêu chí: bằng chứng đúng vị trí, lý do hỗ trợ kết luận, không suy diễn hành vi thiếu căn cứ. Lưu điểm ban đầu, bất đồng và kết quả thống nhất.

## 4. Kế hoạch theo tuần

### Tuần 1 — 05/11–11/11: Chốt thiết kế và chạy pilot

**Nhu**

- [ ] Khảo sát archive, metadata và script cài đặt của npm/PyPI.
- [ ] Kiểm tra cấu trúc, nhãn, ngày tháng và khả năng lấy mẫu từ Datadog/OpenSSF.
- [ ] Thiết kế quy trình tải, giải nén và đọc mẫu trong môi trường cô lập.
- [ ] Đề xuất data manifest và tiêu chí chọn mẫu lành tính.

**Hiếu**

- [ ] Tạo repo, cấu trúc module, cấu hình và quy ước lưu log.
- [ ] Chạy GuardDog và một LLM ứng viên trên tập pilot nhỏ.
- [ ] Ghi nhận token, latency, giới hạn ngữ cảnh và lỗi đầu ra.
- [ ] Khảo sát lockfile; chọn phiên bản và cú pháp CLI sẽ hỗ trợ.

**Cả hai**

- [ ] Chốt RQ, giao diện dữ liệu giữa extractor/ML/LLM/report và phạm vi CLI.
- [ ] Lập dàn ý khóa luận, danh mục tài liệu và bản nháp phần mở đầu.

**Đầu ra:** giao thức thực nghiệm v1, manifest/schema v1, repo, log pilot và đặc tả CLI.

**Nghiệm thu:** một archive đi được qua luồng đọc tĩnh và baseline; hai thành viên sử dụng được cùng schema; có ước lượng chi phí ban đầu.

### Tuần 2 — 12/11–18/11: Tạo dữ liệu và khóa tập đánh giá

**Nhu**

- [ ] Thu thập mẫu, đối chiếu nhãn và mốc thời gian.
- [ ] Loại trùng hash, nhóm gần trùng và thống kê các nhóm xuyên thời gian.
- [ ] Chia train/validation/test; xuất danh sách mẫu và thống kê theo lớp/hệ sinh thái.
- [ ] Viết bản nháp chương dữ liệu.

**Hiếu**

- [ ] Hoàn thiện GuardDog batch runner và chuẩn hóa output.
- [ ] Viết downloader nhận tên/phiên bản, không cài hoặc build gói.
- [ ] Tạo evaluator và schema dự đoán chung cho tất cả phương pháp.
- [ ] Chốt model LLM chính, ngân sách token và giới hạn retry từ pilot.

**Cả hai**

- [ ] Rà nhãn lành tính, leakage, dữ liệu thiếu và thiên lệch nguồn.
- [ ] Chốt tập con đánh giá LLM nếu cần; khóa test bằng manifest và hash.
- [ ] Chốt quy mô robustness, tiêu chí giải thích và cách tính ngân sách.

**Đầu ra:** dataset v1, manifest chia tập, báo cáo chất lượng dữ liệu, batch baseline và ngân sách LLM.

**Nghiệm thu:** không có nhóm trùng/gần trùng xuyên tập theo quy tắc đã chọn; có đủ dữ liệu để triển khai các phép so sánh chính; mọi mẫu bị loại có lý do.

### Tuần 3 — 19/11–25/11: Hoàn thiện đặc trưng và các prompt

**Nhu**

- [ ] Trích xuất script cài đặt, truy cập mạng, biến môi trường và tệp nhạy cảm.
- [ ] Trích xuất thực thi mã động, chuỗi mã hóa và dấu hiệu obfuscation.
- [ ] Bổ sung metadata, tín hiệu tên gói và đặc trưng thống kê.
- [ ] Xuất feature matrix, cờ thiếu dữ liệu và kiểm thử extractor.

**Hiếu**

- [ ] Xây dựng file selector và giới hạn token nhất quán.
- [ ] Viết prompt zero-shot, few-shot và prompt có bằng chứng tĩnh.
- [ ] Tạo JSON schema, kiểm tra đầu ra, logging và cache theo cấu hình/input.
- [ ] Chạy thử trên validation; thiết kế parser CLI cho hai định dạng dependency.

**Cả hai**

- [ ] Rà schema tích hợp và kiểm tra không lộ nhãn trong input.
- [ ] Cập nhật chương phương pháp, sơ đồ kiến trúc và sổ thí nghiệm.

**Đầu ra:** extractor v1, feature schema, ba prompt và LLM runner.

**Nghiệm thu:** cùng input/cấu hình tạo được dữ liệu có truy vết; lỗi parse và vượt giới hạn được ghi nhận rõ.

### Tuần 4 — 26/11–02/12: Chọn baseline bằng validation

**Nhu**

- [ ] Huấn luyện RF và XGBoost với preprocessing chỉ fit trên train.
- [ ] Tìm siêu tham số trong phạm vi hữu hạn, lưu seed và model artifact.
- [ ] So sánh ML với GuardDog trên validation; phân tích FP/FN và feature importance.
- [ ] Chạy ablation metadata.

**Hiếu**

- [ ] So sánh ba chiến lược prompt trên cùng validation subset.
- [ ] Tổng hợp token, latency, chi phí, JSON lỗi và chất lượng bằng chứng.
- [ ] Chọn prompt/model; hoàn thiện prompt phân định dữ liệu không tin cậy.
- [ ] Phát triển phép thử injection và prompt phòng vệ bằng validation.

**Cả hai**

- [ ] Chốt cấu hình ứng viên cho hybrid và giới hạn suy giảm recall cần đánh giá.
- [ ] Rà leakage, log cấu hình và cập nhật bản thảo phương pháp.

**Đầu ra:** bảng validation, cấu hình baseline, kết quả ablation ban đầu và quyết định chọn phương pháp.

**Nghiệm thu:** quyết định chọn mô hình/prompt có bằng chứng validation; chưa dùng kết quả test.

### Tuần 5 — 03/12–09/12: Tích hợp hybrid và đóng băng phương pháp

**Nhu**

- [ ] Khảo sát ngưỡng ML trên validation: recall, FPR và tỷ lệ chuyển LLM.
- [ ] Chọn ngưỡng theo tiêu chí đã chốt; phân tích mẫu độc hại bị bỏ qua.
- [ ] Đóng gói inference trả score, nhãn và phiên bản feature/model.

**Hiếu**

- [ ] Tích hợp ML, LLM và decision rules cho mọi nhánh.
- [ ] Xử lý timeout, JSON lỗi, retry, cache và báo cáo coverage.
- [ ] Kiểm thử end-to-end, gồm nhánh bỏ qua LLM và LLM thất bại.
- [ ] Hoàn thiện CLI archive tối thiểu để dùng cho chạy thực nghiệm.

**Cả hai**

- [ ] Khóa model, prompt, ngưỡng, phiên bản GuardDog, bộ luật và evaluator.
- [ ] Khóa thiết kế robustness; kiểm tra ngân sách và chạy thử quy trình trên validation.
- [ ] Hoàn thiện bản nháp chương thiết kế hybrid.

**Đầu ra:** hybrid MVP, CLI archive, cấu hình đóng băng và biên bản sẵn sàng chạy test.

**Nghiệm thu:** truy vết được kết quả từng tầng; lỗi không biến thành nhãn lành tính; pipeline tính đúng số lượt gọi LLM và false negative toàn luồng.

### Tuần 6 — 10/12–16/12: Chạy thực nghiệm chính

**Nhu**

- [ ] Chạy RF/XGBoost và ablation theo cấu hình đóng băng.
- [ ] Tính metrics, confusion matrix và khoảng tin cậy phù hợp.
- [ ] Tổng hợp theo npm/PyPI; phân tích FP/FN và độ phủ.

**Hiếu**

- [ ] Chạy GuardDog, LLM độc lập và hybrid trên cùng tập so sánh.
- [ ] Đo số lượt gọi, token, retry, latency và chi phí thực tế.
- [ ] Tổng hợp khác biệt giữa LLM độc lập và hybrid, gồm lỗi do tầng ML.

**Cả hai**

- [ ] Chấm giải thích độc lập trên tập đã chọn.
- [ ] Kiểm tra lại một phần kết quả để đánh giá tính tái lập và biến động LLM.
- [ ] Hoàn thành bảng kết quả trung tâm và bản nháp chương thực nghiệm.

**Đầu ra:** predictions từng mẫu, bảng metrics/chi phí/thời gian, phiếu chấm giải thích và phân tích lỗi v1.

**Nghiệm thu:** mọi con số truy được về output và config; không so sánh trực tiếp các phương pháp dùng tập test khác nhau.

### Tuần 7 — 17/12–23/12: Chống chịu và chốt kết quả

**Nhu**

- [ ] Tạo các cặp mẫu gốc/obfuscation theo thiết kế đã khóa.
- [ ] Đánh giá GuardDog và ML; phân tích đặc trưng bị ảnh hưởng.
- [ ] Kiểm tra cú pháp/phép biến đổi và ghi các giới hạn bảo toàn hành vi.

**Hiếu**

- [ ] Đánh giá LLM và hybrid trên tập obfuscation đã chọn.
- [ ] Chạy prompt injection và cấu hình phòng vệ đã chọn từ validation.
- [ ] Tính tỷ lệ tấn công thành công, thay đổi bằng chứng và lỗi đầu ra.

**Cả hai**

- [ ] Viết threats to validity: nhãn, nguồn dữ liệu, leakage, thời gian, model và cỡ mẫu.
- [ ] Khóa bảng/hình chính, hoàn thành nội dung thực nghiệm và gửi CBHD góp ý.

**Đầu ra:** báo cáo robustness, bảng/hình thực nghiệm v1 hoàn chỉnh và bản thảo các chương chính.

**Nghiệm thu:** phân biệt kết quả trước/sau, mẫu qua/không qua LLM; không tinh chỉnh lại phương pháp bằng tập test sau khi xem kết quả.

### Tuần 8 — 24/12–30/12: Hoàn thiện prototype và tái lập

**Nhu**

- [ ] Đóng gói extractor/model, dependency lock và môi trường Docker.
- [ ] Kiểm tra dữ liệu thiếu, archive bất thường và môi trường triển khai mới.
- [ ] Kiểm tra script tái tạo dữ liệu, feature matrix và bảng kết quả.

**Hiếu**

- [ ] Hoàn thiện parser `package-lock.json` và `requirements.txt` trong phạm vi đã cam kết.
- [ ] Tích hợp tải archive, loại trùng dependency và xuất báo cáo theo từng mục.
- [ ] Hoàn thiện exit code, JSON report, README và script demo.
- [ ] Kiểm thử các trường hợp `unsupported`, `inconclusive` và `error`.

**Cả hai**

- [ ] Chạy demo archive và hai định dạng dependency trên môi trường sạch.
- [ ] Kiểm tra không có thao tác cài/build/thực thi mã của mẫu.
- [ ] Chuẩn bị demo offline bằng archive và log đã lưu để dự phòng lỗi API.

**Đầu ra:** CLI hoàn chỉnh trong phạm vi, Docker, hướng dẫn tái lập và bộ demo.

**Nghiệm thu:** chạy lại được theo README; báo đúng mục không hỗ trợ, không tuyên bố đã quét toàn bộ dependency nếu còn mục bỏ qua.

### Tuần 9 — 31/12–06/01: Tích hợp báo cáo và xử lý góp ý

**Nhu**

- [ ] Hoàn thiện chương dữ liệu, đặc trưng, ML và thống kê.
- [ ] Kiểm tra số liệu, bảng/hình và diễn giải hạn chế dữ liệu.

**Hiếu**

- [ ] Hoàn thiện chương LLM, hybrid, chi phí, robustness và prototype.
- [ ] Viết bàn luận về điều kiện hybrid có lợi hoặc không có lợi.

**Cả hai**

- [ ] Tích hợp báo cáo v1, thống nhất thuật ngữ, trích dẫn và phụ lục.
- [ ] Xử lý góp ý CBHD; rà từng RQ đã được trả lời bằng kết quả nào.
- [ ] Chỉ chạy bổ sung để sửa lỗi đo lường hoặc làm rõ kết quả; ghi phiên bản và lý do, không chọn lại cấu hình theo test.

**Đầu ra:** báo cáo v1 đầy đủ, danh sách góp ý và bảng đối chiếu RQ–kết quả.

**Nghiệm thu:** không còn chương chính để trống; số liệu báo cáo khớp output.

### Tuần 10 — 07/01–13/01: Hoàn thiện báo cáo, slide và diễn tập

**Nhu**

- [ ] Chốt nội dung dữ liệu/ML, bảng/hình và phụ lục phụ trách.
- [ ] Chuẩn bị slide dữ liệu, baseline và kết quả.

**Hiếu**

- [ ] Chốt nội dung LLM/hybrid/CLI và kết luận có căn cứ.
- [ ] Chuẩn bị slide kiến trúc, đánh đổi chi phí và demo.

**Cả hai**

- [ ] Hoàn thiện báo cáo v2 và gửi CBHD góp ý cuối.
- [ ] Diễn tập, phân chia thời lượng, chuẩn bị câu hỏi phản biện.
- [ ] Khóa tính năng mới; kiểm tra gói bàn giao và kịch bản dự phòng.

**Đầu ra:** báo cáo gần cuối, slide, demo ổn định và danh sách câu hỏi phản biện.

**Nghiệm thu:** trình bày được đóng góp, giới hạn, nguồn dữ liệu và nguyên nhân chọn ngưỡng; demo chạy lại được.

### Tuần 11 — 14/01–17/01: Chỉnh sửa cuối và nộp

**Nhu**

- [ ] Áp dụng góp ý cuối về dữ liệu/ML; rà bảng, hình và phụ lục.

**Hiếu**

- [ ] Áp dụng góp ý cuối về LLM/hybrid/CLI; kiểm tra repo và README.
- [ ] Xuất bản PDF cuối, kiểm tra mục lục, liên kết và bố cục.

**Cả hai**

- [ ] Kiểm tra yêu cầu nộp, biểu mẫu, chữ ký và xác nhận theo quy định thực tế.
- [ ] Lưu báo cáo, slide, code, config, manifests và kết quả cuối.
- [ ] Nộp trước hoặc đúng ngày 17/01/2027; lưu minh chứng nộp.

**Đầu ra:** hồ sơ nộp hoàn chỉnh và bản lưu trữ có thể truy vết.

**Nghiệm thu:** đủ tài liệu, mở được các tệp cuối, khớp phiên bản code/kết quả và có minh chứng nộp.

## 5. Mốc kiểm soát và điều kiện chuyển giai đoạn

| Mốc | Hạn | Điều kiện đạt | Nếu chưa đạt |
| --- | --- | --- | --- |
| M1: Chốt thiết kế | 11/11/2026 | Có schema, RQ, phạm vi CLI và pilot | Dừng mở rộng công cụ/model; ưu tiên chạy một luồng mẫu |
| M2: Khóa dữ liệu | 18/11/2026 | Có split, hash, kiểm tra leakage và quy mô khả thi | Giảm số mẫu nhưng giữ hai hệ sinh thái/hai lớp; công bố giới hạn |
| M3: Chọn baseline | 02/12/2026 | Có validation cho GuardDog/ML/LLM | Giới hạn tìm siêu tham số và số LLM; không bỏ baseline bắt buộc |
| M4: Khóa phương pháp | 09/12/2026 | Hybrid chạy, ngưỡng và decision rules cố định | Dùng cấu hình đơn giản nhất đạt điều kiện chạy và có truy vết |
| M5: Chốt thực nghiệm | 23/12/2026 | Có bảng chính, robustness giới hạn và phân tích lỗi | Cắt phép thử mở rộng; ưu tiên kết quả chính và ghi thiếu hụt |
| M6: Hoàn thành prototype | 30/12/2026 | CLI archive và dependency trong phạm vi chạy được | Giữ đúng phạm vi tối thiểu; không thêm UI hoặc định dạng mới |
| M7: Báo cáo đầy đủ | 06/01/2027 | Có tất cả chương, số liệu khớp | Ưu tiên biên tập, không mở nghiên cứu mới |
| M8: Sẵn sàng nộp | 13/01/2027 | Báo cáo, slide và demo ổn định | Chỉ sửa lỗi và góp ý thiết yếu |

## 6. Ngân sách, rủi ro và thời gian dự phòng

### 6.1. Ngân sách LLM

Cuối tuần 2 phải lưu một bảng ước lượng gồm model, giá tại thời điểm chạy, số mẫu, số lượt gọi và token trung bình từ pilot.

- Ngân sách cơ bản: pilot + ba chiến lược prompt trên validation + LLM độc lập trên test + LLM được gọi trong hybrid.
- Ngân sách bổ sung: ablation chưa được bao phủ, robustness, kiểm tra độ ổn định và retry.
- Chi phí mỗi lượt = token input × đơn giá input + token output × đơn giá output, có điều chỉnh theo cơ chế tính giá/cache thực tế.
- Có hạn mức dừng cho chi phí/token; ghi log cả lượt lỗi và retry có tính phí.
- Cache gắn với hash input, prompt và model/config. Tách kết quả có cache và lần đo thực sự gọi model để tránh làm sai so sánh latency/chi phí.

Nếu thiếu ngân sách, giảm số mẫu LLM bằng một tập con chung đã chọn trước; không chỉ giữ những mẫu dễ hoặc mẫu có kết quả thuận lợi.

### 6.2. Rủi ro cần theo dõi

| Rủi ro | Người theo dõi | Biện pháp |
| --- | --- | --- |
| Thiếu archive, thiếu ngày phát hành hoặc nhãn không chắc chắn | Nhu | Pilot sớm, thống kê mẫu loại, điều chỉnh quy mô trước khi khóa split |
| Thiên lệch Datadog về GuardDog | Cả hai | Nêu selection bias; dùng tập nguồn độc lập nếu thu thập được trong lịch, không mặc nhiên coi OpenSSF là độc lập |
| Rò rỉ do mẫu gần trùng hoặc metadata tương lai | Nhu | Nhóm gần trùng, tách thời gian, ghi mốc metadata và kiểm tra input |
| ML bỏ sót trước khi LLM được gọi | Cả hai | Chọn ngưỡng trên validation, đo recall toàn luồng và phân tích false negative tầng đầu |
| API lỗi, vượt ngân sách hoặc model thay đổi | Hiếu | Khóa model/version nếu nhà cung cấp hỗ trợ, log config, giới hạn retry, lưu input/output và demo offline |
| Parser/file selector bỏ qua mã độc | Cả hai | Ghi coverage, tệp bị bỏ qua, giới hạn kích thước và phân tích các trường hợp thiếu ngữ cảnh |
| Dependency không xác định được archive | Hiếu | Hỗ trợ cú pháp đã cam kết, báo `unsupported`, lưu artifact/hash đã quét |
| Mẫu bị thực thi ngoài ý muốn hoặc giải nén gây hại | Cả hai | Xử lý trong môi trường cô lập; chặn path traversal/symlink không phù hợp, giới hạn kích thước/số tệp; không cài/build/chạy mẫu |
| Báo cáo bị dồn cuối kỳ | Cả hai | Viết từng chương theo tiến độ; gửi bản thảo chính cuối tuần 7 |

### 6.3. Dự phòng và thứ tự cắt giảm

- Chỉ lập lịch khoảng 80–85% quỹ thời gian nghiên cứu thực tế của mỗi người; giữ phần còn lại cho dữ liệu lỗi, sửa tích hợp và chạy lại cần thiết.
- Sau tuần 5 không thêm baseline, hệ sinh thái hoặc kiến trúc mới.
- Khi trễ, cắt theo thứ tự: LLM thứ hai → tìm siêu tham số mở rộng → thêm phép obfuscation/injection → giao diện và định dạng CLI ngoài phạm vi.
- Giữ các đầu ra cốt lõi: hai hệ sinh thái, baseline đã cam kết, so sánh công bằng, hybrid có truy vết, thử nghiệm chống chịu giới hạn, CLI tối thiểu và báo cáo.
- Nếu buộc phải thay đổi một đầu ra đã cam kết trong đề cương, ghi rõ tác động và trao đổi CBHD trước khi coi đó là phạm vi mới.

## 7. Quy ước theo dõi công việc

Mỗi nhiệm vụ triển khai được ghi theo mẫu:

| Trường | Nội dung |
| --- | --- |
| Mã | Ví dụ `W02-N01`, `W05-H02`, `W06-C01` |
| Người chịu trách nhiệm | Một người chính; nhiệm vụ chung có một người điều phối |
| Phụ thuộc | Mã nhiệm vụ hoặc đầu ra phải có trước |
| Ước lượng | Số giờ dự kiến, cập nhật khi có dữ liệu thực tế |
| Hạn | Ngày hoàn thành cụ thể |
| Tiêu chí hoàn thành | Kết quả quan sát/kiểm tra được |
| Trạng thái | Chưa cập nhật / Chưa bắt đầu / Đang thực hiện / Bị chặn / Hoàn thành |
| Minh chứng | Commit, config, manifest, log, bảng kết quả hoặc bản thảo |
| Vướng mắc | Nguyên nhân, người xử lý và bước tiếp theo |

- Các checkbox trong kế hoạch là checklist bàn giao, không phải báo cáo tiến độ thực tế đã xác minh.
- Đầu tuần: chọn nhiệm vụ, ước lượng giờ và xác định phụ thuộc. Cuối tuần: nghiệm thu bằng minh chứng và cập nhật rủi ro.
- Họp ngắn giữa tuần để xử lý tích hợp; không chờ đến cuối tuần mới báo bị chặn.
- Phân biệt tỷ lệ nhiệm vụ hoàn thành với tỷ lệ khối lượng công việc. Không suy ra tiến độ theo thời gian chỉ từ số task.
- Mọi lần chạy thí nghiệm lưu run ID, commit, config, seed, hash manifest, model/prompt version và thời điểm chạy.
- Thay đổi sau khi mở test phải có lý do và phiên bản. Phân biệt sửa lỗi triển khai với điều chỉnh phương pháp; điều chỉnh phương pháp bằng kết quả test phải được công bố là thăm dò, không giữ cách diễn giải test độc lập ban đầu.

## 8. Checklist bàn giao cuối

- [ ] Báo cáo trả lời từng RQ, nêu kết quả thuận lợi và bất lợi.
- [ ] Có thống kê nhãn, nguồn, hệ sinh thái, split và mẫu bị loại.
- [ ] Có predictions, metrics, chi phí, thời gian, coverage và phân tích FP/FN.
- [ ] Có cấu hình GuardDog/RF/XGBoost/LLM/hybrid cùng phiên bản tương ứng.
- [ ] Có mô tả leakage, selection bias, sai nhãn, cỡ mẫu và giới hạn đánh giá lịch sử.
- [ ] Có kết quả robustness và tiêu chí chấm giải thích.
- [ ] CLI hỗ trợ archive và hai dạng dependency trong phạm vi đã chốt.
- [ ] README đủ để chạy lại trên môi trường mới; không chứa API key.
- [ ] Manifest và hướng dẫn lấy dữ liệu phù hợp điều kiện chia sẻ; không mặc định công khai archive mã độc trong repo code.
- [ ] Báo cáo PDF, slide và demo khớp phiên bản kết quả cuối.
- [ ] Đủ biểu mẫu/xác nhận theo yêu cầu của khoa và có minh chứng nộp.

## 9. Tài liệu cơ sở

- Đề cương gốc: [De_cuong_KLTN.docx](./De_cuong_KLTN.docx).
- Bảng kế hoạch đã đối chiếu: [Google Sheets](https://docs.google.com/spreadsheets/d/1GER8ppaZhPaQpj1UpLxPD5x7ShWf17v0QM76PUXHb_c/edit?gid=770003).
- [Datadog Malicious Software Packages Dataset](https://github.com/DataDog/malicious-software-packages-dataset): xác minh quy mô theo hệ sinh thái, ngày phát hiện, nhãn và selection bias tại snapshot sử dụng.
- [GuardDog](https://github.com/DataDog/guarddog): xác minh cơ chế quét và cố định phiên bản/bộ luật.
- [OpenSSF malicious-packages](https://github.com/ossf/malicious-packages): đối chiếu thông tin gói, phiên bản và nguồn bằng chứng.
