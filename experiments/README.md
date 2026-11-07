# Experiment registry

Mỗi run tạo một thư mục trong `experiments/runs/<run_id>/` gồm `config.toml`, `metadata.json`, `manifest.sha256`, `predictions.jsonl`, `metrics.json` và `README.md`. Thư mục run bị loại khỏi Git nếu chứa output lớn.
