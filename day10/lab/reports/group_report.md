# Báo Cáo Nhóm - Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Vin_Lab10  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|---|---|---|
|Lê Trung Anh Quốc|Ingestion, Cleaning, Embed, Monitoring |leanhquoc128@gmail.com|

**Ngày nộp:** 2026-04-15  
**Repo:** local workspace

---

Pipeline chạy theo chuỗi ingest -> clean -> validate -> embed. Dữ liệu đầu vào là `data/raw/policy_export_dirty.csv`, chứa nhiều lỗi mô phỏng thực tế (duplicate, stale policy, doc_id lạ, thiếu ngày hiệu lực). Mỗi lần chạy sinh log có `run_id`, số lượng raw/cleaned/quarantine và manifest để theo dõi lineage/freshness. Sau cleaning, dữ liệu được validate bằng bộ **Pydantic Model** (chống lỗi schema tiềm ẩn) và expectation suite (phân tách `halt` và `warn`) trước khi publish vào Chroma.

Lệnh chạy chuẩn:

`python etl_pipeline.py run --run-id sprint2`

---

## 2. Cleaning & expectation

Nhóm đã mở rộng cleaning rules theo hướng có đo lường được tác động (`metric_impact[...]`) và thêm expectation mới phục vụ observability.

### 2a. Bảng metric_impact

| Rule / Expectation mới | Trước (inject-bad) | Sau (recover-good) | Chứng cứ |
|---|---:|---:|---|
| `rule_fix_stale_refund_window` | 0 | 1 | `artifacts/logs/run_sprint3-inject.log`, `run_sprint3.log` |
| `rule_pydantic_validation_error` | 0 | 0 | `run_sprint2-pydantic-distinction.log` (Bonus points) |
| `rule_refund_migration_note_removed` | 1 | 1 | `artifacts/logs/run_sprint3.log` |
| `rule_quarantine_semantic_duplicate_chunk_text` | 1 | 1 | `artifacts/logs/run_sprint3.log` |
| `expectation[refund_no_stale_14d_window]` | FAIL (`violations=1`) | OK (`violations=0`) | `artifacts/logs/run_sprint3-inject.log`, `run_sprint3.log` |
| `expectation[exported_at_iso_datetime]` | OK | OK | `artifacts/logs/run_sprint3.log` |

Expectation halt chính: `refund_no_stale_14d_window`, `effective_date_iso_yyyy_mm_dd`, `exported_at_iso_datetime`.

---

## 3. Before / after ảnh hưởng retrieval

Kịch bản inject dùng `--run-id sprint3-inject --no-refund-fix --skip-validate` để cố ý publish dữ liệu xấu. Kết quả eval cho `q_refund_window` ở `after_inject_bad.csv` cho thấy `hits_forbidden=yes`, tức top-k vẫn chứa chunk stale 14 ngày dù retrieval vẫn có thể chứa từ khóa mong đợi. Sau khi chạy `sprint3` (có fix), file `before_after_eval.csv` chuyển về `hits_forbidden=no`, đồng thời preview top-1 thể hiện nội dung 7 ngày và marker `[cleaned: stale_refund_window]`.

Với `q_leave_version`, cả trước và sau đều ổn định (`contains_expected=yes`, `top1_doc_expected=yes`), chứng minh rule quarantine HR cũ hoạt động nhất quán.

---

## 4. Freshness & monitoring

Freshness check từ `manifest_sprint3.json` trả về `FAIL` vì `latest_exported_at` cũ hơn SLA 24 giờ. Đây là hành vi hợp lý với dữ liệu mẫu tĩnh của lab. Runbook ghi rõ cách diễn giải PASS/WARN/FAIL và hành động tương ứng (rerun với snapshot mới hơn hoặc điều chỉnh SLA theo policy).

---

## 5. Liên hệ Day 09

Collection `day10_kb` là lớp dữ liệu đã qua clean/validate, có thể dùng làm nguồn retrieval ổn định cho hệ multi-agent Day 09. Việc giữ idempotent publish boundary (upsert + prune) giúp tránh vector stale gây sai ngữ cảnh cho agent.

---

## 6. Rủi ro còn lại & việc chưa làm

- Chưa cấu hình cảnh báo tự động theo kênh chatops.
- Chưa mở rộng bộ câu hỏi eval beyond baseline.
- Cần bổ sung đầy đủ file individual report cho toàn bộ thành viên nhóm trước khi nộp final.

**Minh chứng Distinction:**
- Đã tích hợp **Pydantic Model** (`CleanedRow`) để validate schema cuối cùng trước khi embed.
- Đã cấu hình `HR_LEAVE_STALE_CUTOFF` trong `.env` thay vì hard-code ngày trong code (linh hoạt cho vận hành).
- Freshness check tự động ghi lại Run ID và lineage qua manifest.

---

## Peer review (Phần E) (Từ người của nhóm khác)

1. **Rule/expectation nào đang có tín hiệu giả dương hoặc giả âm?**
   - **Trả lời:** Rule lọc các câu văn quá ngắn (dưới 24 ký tự) dễ gây ra sai sót nhất. Có những tên điều khoản tuy ngắn nhưng lại rất quan trọng cho việc tìm kiếm chính xác. Giải pháp là gộp các đoạn ngắn này vào nội dung phía sau thay vì đưa vào quarantine.
2. **Nếu Jina API lỗi tạm thời, nhóm degrade pipeline ở điểm nào để không mất dữ liệu?**
   - **Trả lời:** Hệ thống sẽ tạm dừng tại bước Embedding. Do dữ liệu sạch đã được kiểm định và lưu trữ an toàn trong file CSV, chúng ta có thể thực hiện Embed lại sau khi API hoạt động bình thường mà không cần xử lý lại dữ liệu thô từ đầu.
3. **SLA freshness nên đo ở ingest boundary hay publish boundary cho use case này?**
   - **Trả lời:** Nên thực hiện đo ở cả hai ranh giới. Ingest boundary giúp xác định độ mới của dữ liệu từ nguồn cấp, còn Publish boundary đo lường hiệu suất xử lý của chính pipeline. Việc kết hợp cả hai đầu giúp tôi dễ dàng xác định nguyên nhân nếu dữ liệu bị cũ.
