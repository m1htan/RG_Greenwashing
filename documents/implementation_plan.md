# Implementation Plan: Gemini 2.5-Pro ESG Extraction Pipeline

## Goal
Build a Python script that sends all 823 sustainability report PDFs to Gemini 2.5-pro API for ESG field extraction, outputting results as a structured CSV for greenwashing research and ESG scoring.

## User Review Required

> [!IMPORTANT]
> **Chi phí API ước tính**: Gemini 2.5-pro pricing (as of March 2025):
> - Input: $1.25/1M tokens (≤200K), $2.50/1M tokens (>200K)
> - Output: $10/1M tokens (≤200K), $15/1M tokens (>200K)
> - PDFs bao gồm cả image tokens
>
> Với 823 PDFs (trung bình ~80 pages), ước tính **~$50-150 tổng cộng** tùy vào độ dài nội dung.
>
> **Bạn cần cung cấp Gemini API key** vào file [config/.env](file:///d:/Github/RG_Greenwashing/config/.env). Bạn có sẵn key chưa?

> [!WARNING]
> **Files > 50MB**: Gemini Files API giới hạn 50MB/file. Có **3 file > 50MB** (max 410MB). Với các file này, script sẽ dùng PyMuPDF extract text trước rồi gửi text thay vì file gốc.

---

## Proposed Changes

### Core Module

#### [NEW] [extract_esg_fields.py](file:///d:/Github/RG_Greenwashing/scripts/extract_esg_fields.py)

Script chính — xử lý tất cả 823 PDFs qua Gemini 2.5-pro API.

**Chức năng chính:**
1. **Load metadata** từ [vietnam_reports.json](file:///d:/Github/RG_Greenwashing/data/vietnam_sustainabilityreports/vietnam_reports.json) + [vietnam_companies.json](file:///d:/Github/RG_Greenwashing/data/vietnam_sustainabilityreports/vietnam_companies.json) → mapping PDF filename ↔ company/report info
2. **Scan `pdfs/` folder** → danh sách PDFs cần xử lý
3. **Check existing results** → skip PDFs đã xử lý (resume logic)
4. **Cho mỗi PDF:**
   - Nếu file ≤ 50MB: upload qua Gemini Files API → gửi prompt
   - Nếu file > 50MB: dùng PyMuPDF extract text → gửi text prompt
   - Parse JSON response → validate fields
   - Append row vào CSV
5. **Rate limiting**: delay giữa các requests (tránh quota)
6. **Error handling**: retry 3 lần, log lỗi, tiếp tục file tiếp theo

**Structured extraction prompt** sẽ yêu cầu Gemini trả về JSON với schema cố định gồm ~30 fields.

**CLI arguments:**
```
python scripts/extract_esg_fields.py
  --pdf-dir data/vietnam_sustainabilityreports/pdfs
  --reports-json data/vietnam_sustainabilityreports/vietnam_reports.json
  --companies-json data/vietnam_sustainabilityreports/vietnam_companies.json
  --output data/esg_extracted.csv
  --skip-existing          # resume từ CSV đã có
  --delay 2                # seconds giữa các API calls
  --max-files N            # giới hạn số file (debug)
  --log-file logs/extraction.log
```

**CSV Output Schema (30 fields):**

| # | Column | Type | Mô tả |
|---|--------|------|--------|
| 1 | `pdf_filename` | str | Tên file PDF |
| 2 | `company_name` | str | Tên công ty |
| 3 | `company_ticker` | str | Mã CK |
| 4 | `company_sector` | str | Ngành |
| 5 | `report_year` | int | Năm báo cáo |
| 6 | `report_type` | str | SR/AR/AR+/IR |
| 7 | `report_lang` | str | EN/VI |
| 8 | `report_pages` | int | Số trang |
| 9 | `gri_standards` | str | Danh sách GRI codes (comma-separated) |
| 10 | `sdgs` | str | SDGs được nhắc (comma-separated) |
| 11 | `frameworks` | str | GRI/TCFD/SASB/ISSB/UNGC/CDP (comma-separated) |
| 12 | `external_assurance` | str | Tên đơn vị kiểm toán (PwC/KPMG/EY/Deloitte) hoặc "None" |
| 13 | `ghg_scope1` | str | Phát thải Scope 1 (giá trị + đơn vị) |
| 14 | `ghg_scope2` | str | Phát thải Scope 2 |
| 15 | `ghg_scope3` | str | Phát thải Scope 3 |
| 16 | `total_energy_consumption` | str | Tổng tiêu thụ năng lượng |
| 17 | `renewable_energy_pct` | str | % năng lượng tái tạo |
| 18 | `water_consumption` | str | Tổng tiêu thụ nước |
| 19 | `total_waste` | str | Tổng chất thải |
| 20 | `waste_recycled_pct` | str | % chất thải tái chế |
| 21 | `total_employees` | str | Tổng số nhân viên |
| 22 | `female_employee_pct` | str | % nhân viên nữ |
| 23 | `female_leadership_pct` | str | % nữ lãnh đạo |
| 24 | `training_hours_per_employee` | str | Giờ đào tạo/nhân viên |
| 25 | `ltifr` | str | Lost Time Injury Frequency Rate |
| 26 | `community_investment` | str | Đầu tư cộng đồng (VND) |
| 27 | `has_net_zero_commitment` | bool | Có cam kết Net Zero? |
| 28 | `net_zero_target_year` | str | Năm mục tiêu Net Zero |
| 29 | `key_esg_commitments` | str | Tóm tắt các cam kết ESG chính (max 500 chars) |
| 30 | `vagueness_assessment` | str | Đánh giá mức độ mơ hồ: "low/medium/high" |
| 31 | `quantitative_data_richness` | str | Đánh giá mức độ có số liệu cụ thể: "low/medium/high" |
| 32 | `extraction_status` | str | "success" / "error: ..." |

---

#### [MODIFY] [.env](file:///d:/Github/RG_Greenwashing/config/.env)

Thêm `GEMINI_API_KEY`.

---

#### [MODIFY] [requirements.txt](file:///d:/Github/RG_Greenwashing/requirements.txt)

Thêm dependencies:
```
google-genai>=1.0
pymupdf>=1.25
python-dotenv>=1.0
```

---

## Verification Plan

### Automated Tests

1. **Dry-run test (1 file)**:
```bash
python scripts/extract_esg_fields.py --pdf-dir data/vietnam_sustainabilityreports/pdfs --output data/test_extract.csv --max-files 1 --log-file logs/test.log
```
Verify: CSV created with 1 row, all 32 columns present, `extraction_status` = "success"

2. **Resume test (skip-existing)**:
```bash
python scripts/extract_esg_fields.py --pdf-dir data/vietnam_sustainabilityreports/pdfs --output data/test_extract.csv --max-files 3 --skip-existing
```
Verify: Only 2 new rows added (1st file skipped), total 3 rows

3. **Oversized file test**: Manually test with one of the 3 files > 50MB to verify text fallback works

### Manual Verification

- Mở CSV file, kiểm tra nội dung vài hàng có hợp lý không (GRI codes đúng, số liệu tCO2e hợp lý, v.v.)
- Cross-check 1-2 kết quả với PDF gốc bằng mắt
