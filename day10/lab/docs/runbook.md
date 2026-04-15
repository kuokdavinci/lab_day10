# Runbook - Lab Day 10 (incident tối giản)

---

## Symptom

- Agent trả lời đúng một phần nhưng retrieval còn dính chunk stale (ví dụ refund 14 ngày).
- Pipeline có thể `PIPELINE_HALT` khi expectation `halt` fail.
- Monitoring báo `freshness_check=FAIL`.

---

## Detection

- Log ETL: kiểm tra `expectation[...]`, `metric_impact[...]`, `PIPELINE_OK/HALT`.
- Eval CSV: kiểm tra `contains_expected` và `hits_forbidden`.
- Freshness: đọc manifest qua lệnh:
  - `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run-id>.json`

Giải thích status freshness:
- `PASS`: tuổi dữ liệu <= SLA.
- `WARN`: dữ liệu sắp vượt SLA (nếu có ngưỡng cảnh báo).
- `FAIL`: tuổi dữ liệu vượt SLA, cần xử lý trước khi publish cho production.

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|---|---|---|
| 1 | Mở `artifacts/manifests/manifest_<run-id>.json` | Có `run_id`, `latest_exported_at`, số record |
| 2 | Mở `artifacts/quarantine/quarantine_<run-id>.csv` | Thấy rõ `reason` để khoanh vùng lỗi dữ liệu |
| 3 | Mở log `artifacts/logs/run_<run-id>.log` | Thấy expectation fail/passed và metric_impact |
| 4 | Chạy `python eval_retrieval.py --out ...` | So sánh `hits_forbidden` trước/sau fix |

---

## Mitigation

- Trường hợp stale refund: chạy lại pipeline chuẩn có fix (`python etl_pipeline.py run --run-id recover-good`).
- Trường hợp cần demo inject: dùng `--no-refund-fix --skip-validate` và ghi rõ trong báo cáo.
- Trường hợp freshness fail: cập nhật nguồn export mới hơn hoặc điều chỉnh SLA theo policy thực tế.

---

## Prevention

- Duy trì expectation `refund_no_stale_14d_window` ở mức `halt`.
- Theo dõi `metric_impact` theo từng run để phát hiện bất thường sớm.
- Gắn owner/alert channel trong data contract để rõ trách nhiệm vận hành.
