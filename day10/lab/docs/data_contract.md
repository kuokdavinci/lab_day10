# Data contract - Lab Day 10

Bắt đầu từ `contracts/data_contract.yaml` và đồng bộ với tài liệu này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|---|---|---|---|
| `data/raw/policy_export_dirty.csv` (export từ DB/API) | Batch CSV theo mỗi run `etl_pipeline.py run` | Thiếu cột bắt buộc (`doc_id`, `chunk_text`), sai định dạng `exported_at`, `doc_id` ngoài allowlist | `raw_records`, `% invalid_schema`, `% unknown_doc_id`; alert khi `% invalid_schema > 5%` |
| `data/docs/policy_refund_v4.txt` (canonical policy) | Đồng bộ vào corpus docs, sau đó chunk + embed theo `chunk_id` | Nội dung stale (vẫn còn "14 ngày" thay vì "7 ngày"), file canonical chưa cập nhật | `hits_forbidden` cho query refund, `expectation[refund_no_stale_14d_window]`; alert khi `violations > 0` |
| `data/docs/hr_leave_policy.txt` (canonical HR leave) | Đồng bộ vào corpus docs, dùng trong retrieval eval | Version stale (vẫn còn "10 ngày annual leave"), lệch với chính sách mới | `expectation[hr_leave_no_stale_10d_annual]`, số chunk vi phạm theo run; alert khi `violations > 0` |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `chunk_id` | string | Có | ID ổn định để upsert vào vector DB |
| `doc_id` | string | Có | Phải nằm trong `allowed_doc_ids` của contract |
| `chunk_text` | string | Có | Chiều dài tối thiểu 8 ký tự |
| `effective_date` | date | Có | Định dạng `YYYY-MM-DD` |
| `exported_at` | datetime | Có | Dùng để tính freshness SLA |

---

## 3. Quy tắc quarantine vs drop

- Quarantine: record sai schema, thiếu trường bắt buộc, dính stale keyword rule, hoặc vi phạm expectation cần điều tra.
- Drop: chỉ áp dụng với bản ghi không thể khôi phục (ví dụ chunk rỗng sau clean).
- Owner phê duyệt merge lại: `owner_team` trong `contracts/data_contract.yaml`.

---

## 4. Phiên bản và canonical

- Source of truth cho refund policy: `data/docs/policy_refund_v4.txt` (`doc_id=policy_refund_v4`).
- Source of truth cho HR leave: `data/docs/hr_leave_policy.txt`.
- Mọi thay đổi canonical phải kéo theo: cập nhật cleaning rule + expectation + evidence trong `artifacts/eval/`.
