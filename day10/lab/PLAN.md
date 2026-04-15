# PLAN - Lab Day 10 (Data Pipeline & Data Observability)

## Cach dung file nay
- Danh dau `[x]` khi hoan thanh.
- Cap nhat ngay trong qua trinh lam de theo doi tien do that.
- Uu tien lam theo thu tu Sprint 1 -> 4.

## Muc tieu tong quan
- [x] Pipeline chay du luong ingest -> clean -> validate -> embed.
- [x] Co evidence before/after retrieval khi inject du lieu xau va khi fix.
- [x] Co freshness check + docs + report day du theo yeu cau nop bai.

## Sprint 1 - Ingest & Schema (60')

### 1) Khoi tao va setup
- [x] Tao moi truong va cai dependency:
  - `cd lab`
  - `python -m venv .venv`
  - `.venv\Scripts\activate` (Windows) / `source .venv/bin/activate` (Linux/macOS)
  - `pip install -r requirements.txt`
  - `cp .env.example .env` (hoac lenh tuong duong tren Windows)
- [x] Xac nhan file raw co san: `data/raw/policy_export_dirty.csv`.

### 2) Ingest + log baseline
- [x] Chay run dau tien: `python etl_pipeline.py run --run-id sprint1`.
- [x] Kiem tra log/manifests da tao trong:
  - `artifacts/logs/`
  - `artifacts/manifests/`
- [x] DoD Sprint 1 dat:
  - [x] Log co `raw_records`
  - [x] Log co `cleaned_records`
  - [x] Log co `quarantine_records`
  - [x] Log co `run_id`

### 3) Contract/Source map
- [x] Dien source map ngan trong `docs/data_contract.md` (it nhat 2 nguon).
- [x] Moi nguon co failure mode va metric theo doi.

## Sprint 2 - Clean + Validate + Embed (60')

### 1) Mo rong cleaning rules
- [x] Ra soat baseline trong `transform/cleaning_rules.py`.
- [x] Them >= 3 cleaning rule moi (khong trivial).
- [x] Moi rule moi co tac dong do duoc (so lieu truoc/sau, quarantine, expectation fail/pass...).

### 2) Mo rong expectation suite
- [x] Ra soat baseline trong `quality/expectations.py`.
- [x] Them >= 2 expectation moi.
- [x] Kiem tra expectation co the fail dung luc khi inject/fix.

### 3) Chay luong chuan va xac nhan idempotent
- [x] Chay: `python etl_pipeline.py run --run-id sprint2`
- [x] Xac nhan run exit 0 (khong halt ngoai tru demo co chu dich).
- [x] Xac nhan embed idempotent:
  - [x] Upsert theo `chunk_id`
  - [x] Co prune id khong con trong cleaned

### 4) Ghi metric impact vao report
- [x] Cap nhat bang `metric_impact` trong `reports/group_report.md`.
- [x] Co chung minh tac dong cho moi rule/expectation moi.

## Sprint 3 - Inject corruption & Before/After eval (60')

### 1) Tao scenario du lieu xau
- [x] Chay inject co chu dich:
  - `python etl_pipeline.py run --run-id sprint3-inject --no-refund-fix --skip-validate`
- [x] Chay eval sau inject:
  - `python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv`

### 2) Chay lai scenario tot (sau fix)
- [x] Chay lai pipeline chuan (khong inject flags):
  - `python etl_pipeline.py run --run-id sprint3`
- [x] Chay eval:
  - `python eval_retrieval.py --out artifacts/eval/before_after_eval.csv`

### 3) Chung minh before/after
- [x] Co it nhat 2 file eval hoac 1 file co cot `scenario`.
- [x] Co evidence retrieval te hon truoc fix, tot hon sau fix.
- [x] Bat buoc co evidence cho `q_refund_window`.
- [x] Merit: co them evidence cho `q_leave_version` (hoac `gq_d10_03`).
- [x] Hoan thien `docs/quality_report.md` (hoac theo quy dinh giu ten template va ghi ro trong report).

## Sprint 4 - Monitoring + Docs + Reports (60')

### 1) Freshness
- [x] Chay freshness check:
  - `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint3.json`
- [x] Giai thich PASS/WARN/FAIL trong `docs/runbook.md`.

### 2) Hoan thien docs bat buoc
- [x] `docs/pipeline_architecture.md`
- [x] `docs/data_contract.md`
- [x] `docs/runbook.md`
- [x] `docs/quality_report.md` (neu dung ten nay)

### 3) Hoan thien reports
- [x] `reports/group_report.md`
- [ ] Moi thanh vien co 1 file trong `reports/individual/*.md`
- [x] Ghi peer review 3 cau hoi (phan E tren slide) trong group report hoac runbook.

## Checklist Deliverables truoc khi nop
- [x] Code chinh:
  - [x] `etl_pipeline.py`
  - [x] `transform/cleaning_rules.py`
  - [x] `quality/expectations.py`
  - [x] `monitoring/freshness_check.py`
- [x] Contract:
  - [x] `contracts/data_contract.yaml` da dien owner/SLA/nguon
- [x] Artifacts:
  - [x] `artifacts/logs/` co it nhat 1 run tot
  - [x] `artifacts/manifests/` co manifest run tot
  - [x] `artifacts/quarantine/` co evidence records bi cach ly
  - [x] `artifacts/eval/` co evidence inject + recover
- [ ] Docs va report:
  - [x] `docs/*.md` day du
  - [x] `reports/group_report.md` day du
  - [ ] `reports/individual/*.md` day du
- [ ] Grading (neu ap dung):
- [ ] `python grading_run.py --out artifacts/eval/grading_run.jsonl`
- [ ] Co file `artifacts/eval/grading_run.jsonl`

## Optional quick check truoc nop
- [ ] Chay nhanh:
  - `python instructor_quick_check.py --grading artifacts/eval/grading_run.jsonl`
  - `python instructor_quick_check.py --manifest artifacts/manifests/manifest_sprint3.json`

## Tracking tien do theo ngay
- [x] Ngay 1: Sprint 1 + setup report skeleton
- [x] Ngay 2: Sprint 2 (rules + expectations + metric impact)
- [x] Ngay 3: Sprint 3 (inject + eval evidence)
- [x] Ngay 4: Sprint 4 (freshness + docs + final submit checklist)
