# Hợp đồng dữ liệu

Manifest bắt buộc có `sample_id`, ecosystem, package, version, artifact filename, SHA-256, nguồn, snapshot nguồn, label, căn cứ nhãn, ngày phát hành/phát hiện/thu thập và trạng thái xử lý. Không suy ra benign chỉ vì detector không cảnh báo.

Prediction phải lưu `sample_id`, `method`, `run_id`, status, label dự đoán (nếu có), score (nếu có), evidence, latency, input/output token và lỗi/retry. `inconclusive`, `error` và `unsupported` được giữ riêng khi tính coverage; recall vận hành vẫn tính mẫu độc hại chưa phát hiện là bỏ sót.

Feature extractor phải trả schema version, cờ thiếu dữ liệu, danh sách file đã đọc/bỏ qua và evidence có vị trí. Không đưa đường dẫn có nhãn, cảnh báo nguồn hoặc kết luận mã độc vào feature/prompt.
