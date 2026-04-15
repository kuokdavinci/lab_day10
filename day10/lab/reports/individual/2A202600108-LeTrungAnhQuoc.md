# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Lê Trung Anh Quốc
**Vai trò:** Ingestion, Cleaning, Embed, Monitoring  
**Ngày nộp:** 2026-04-15  

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
- `transform/cleaning_rules.py`: Thiết kế toàn bộ luồng Transform, triển khai các cleaning rules mở rộng và tích hợp bộ lọc Pydantic để thẩm định schema.
- `etl_pipeline.py`: Cập nhật logic xử lý lỗi Embedding (try-except block) và triển khai đo lường Freshness tại Ingest boundary (đạt mốc Distinction).
- `quality/expectations.py`: Xây dựng bộ quy tắc kiểm tra chất lượng (Halt/Warn), đặc biệt là rule chặn dữ liệu stale 14 ngày.

**Kết nối với thành viên khác:**
Tôi làm cá nhân
_________________

**Bằng chứng (commit / comment trong code):**
Trong `transform/cleaning_rules.py`, tôi đã khai báo class `CleanedRow(BaseModel)` và hàm `clean_rows` trả về bộ ba `(cleaned, quarantine, impact)`. Các comment trong file ghi rõ mốc **Distinction** và **Bonus** do chính tôi triển khai.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định kỹ thuật quan trọng nhất của tôi là tích hợp **Pydantic Model (`CleanedRow`)** làm bộ lọc cuối cùng trong pha Transform thay vì chỉ dùng regex thủ công. 

Lý do là vì các hàm Regex hay `if-else` thông thường rất dễ bỏ sót các lỗi kiểu dữ liệu phức tạp hoặc các ràng buộc schema chéo nhau. Bằng cách sử dụng Pydantic, tôi đảm bảo rằng 100% bản ghi trước khi đi vào ChromaDB phải vượt qua bước kiểm tra nghiêm ngặt về độ dài chuỗi (`min_length=8`), định dạng ngày (`ISO_DATE`) và danh sách ID tài liệu cho phép (`ALLOWED_DOC_IDS`). 

Tôi thiết lập logic để nếu Pydantic ném ra ngoại lệ `ValidationError`, bản ghi đó sẽ bị đẩy vào `quarantine` với lý do `pydantic_validation_failed`. Quyết định này giúp tách biệt rạch ròi giữa logic "làm sạch" (sửa lỗi) và logic "thẩm định" (đảm bảo tính toàn vẹn), giúp hệ thống đạt chuẩn Data Engineering chuyên nghiệp và cực kỳ dễ bảo trì khi schema thay đổi.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Lỗi: Vi phạm tính Idempotency và dư thừa dữ liệu cũ (Vector DB Stale Orphans)**

**Triệu chứng:** Trong quá trình thử nghiệm, tôi phát hiện khi thực hiện chạy lại (rerun) pipeline trên cùng một tập dữ liệu hoặc khi dữ liệu nguồn bị xóa bớt bản ghi, các bản ghi cũ (stale) vẫn tồn tại trong Vector DB dù đã bị loại bỏ khỏi file Cleaned. Điều này dẫn đến kết quả retrieval bị nhiễu bởi các thông tin lỗi thời và làm phình tài nguyên lưu trữ không cần thiết.

**Metric/Check phát hiện:** Tôi phát hiện qua việc so sánh số lượng IDs hiện có trong collection thông qua `col.get()` với số lượng dòng thực tế trong file `cleaned.csv` sau mỗi lượt chạy.

**Cách khắc phục:** Tôi đã triển khai cơ chế **"Pruning"** (tỉa bỏ) dựa trên ID ổn định ngay trước bước Upsert. Cụ thể, trong hàm `cmd_embed_internal`, tôi thực hiện truy vấn danh sách IDs hiện có, so sánh tập hợp (set difference) với danh sách IDs của lượt chạy hiện tại, và thực hiện lệnh xóa triệt để các ID không còn tồn tại. Giải pháp này đảm bảo tính **Idempotency**, giúp Vector DB luôn là bản sao chính xác của dữ liệu đã qua kiểm định, duy trì độ chính xác cho hệ thống RAG.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Tôi sử dụng `run_id=sprint3-inject` và `sprint3` làm bằng chứng cho rule `rule_fix_stale_refund_window`.

**Trong `before_after_eval.csv`:**
- `sprint3-inject`: `question="q_refund_window", hits_forbidden="yes", top1_preview="...14 ngày..."`
- `sprint3`: `question="q_refund_window", hits_forbidden="no", top1_preview="...7 ngày làm việc [cleaned: stale_refund_window]..."`

Bằng chứng log từ `run_sprint3.log`:
`metric_impact[rule_fix_stale_refund_window]=1`
`expectation[refund_no_stale_14d_window] OK (halt) :: violations=0`

Điều này chứng minh rule làm sạch đã phát hiện chính xác lỗi logic và tự động khôi phục dữ liệu về trạng thái đúng mà không làm gián đoạn retrieval.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ triển khai một **Hệ thống Alerting tích hợp (Slack/Discord Webhook)**. Thay vì chỉ ghi kết quả freshness `FAIL` vào file log, hệ thống sẽ tự động gửi thông báo chi tiết kèm theo `Latest Export Timestamp` và `Reason` vào kênh chatops của nhóm. Việc này giúp đội ngũ vận hành phát hiện sự cố data ngay lập tức mà không cần kiểm soát thủ công các file manifest sau mỗi run.
