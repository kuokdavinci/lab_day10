# Quality report - Lab Day 10 (nhóm)

**run_id before (inject):** `sprint3-inject`  
**run_id after (recover):** `sprint3`  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (sprint3-inject) | Sau (sprint3) | Ghi chú |
|---|---:|---:|---|
| raw_records | 10 | 10 | Không đổi |
| cleaned_records | 6 | 6 | Không đổi |
| quarantine_records | 4 | 4 | Không đổi |
| Expectation halt? | Có (`refund_no_stale_14d_window` fail) | Không | Sau fix pass toàn bộ halt checks |

---

## 2. Before / after retrieval

Artifacts:
- `artifacts/eval/after_inject_bad.csv`
- `artifacts/eval/before_after_eval.csv`

### Câu bắt buộc: `q_refund_window`

- Trước (inject): `hits_forbidden=yes`, top-1 chứa chunk refund 14 ngày.
- Sau (recover): `hits_forbidden=no`, top-1 chứa chunk refund 7 ngày (`[cleaned: stale_refund_window]`).

### Merit: `q_leave_version`

- Trước: `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`.
- Sau: `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`.

---

## 3. Freshness & monitor

- Lệnh: `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint3.json`
- Kết quả: `FAIL` do `latest_exported_at=2026-04-10T08:00:00` vượt SLA 24h.
- Diễn giải: đây là snapshot dữ liệu mẫu cũ; pipeline vẫn chạy đúng nhưng data recency không đạt SLA vận hành.

---

## 4. Corruption inject (Sprint 3)

- Inject bằng: `python etl_pipeline.py run --run-id sprint3-inject --no-refund-fix --skip-validate`.
- Evidence fail/pass:
  - Inject: `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`
  - Recover: `expectation[refund_no_stale_14d_window] OK (halt) :: violations=0`

---

## 5. Hạn chế & việc chưa làm

- Chưa có alert tự động ra kênh chatops.
- Chưa mở rộng eval theo nhiều data slices ngoài bộ câu hỏi baseline.
