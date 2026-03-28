# Phân Tích Dữ Liệu Vietnam Sustainability Reports

## 1. Tổng Quan Dữ Liệu

### Nguồn dữ liệu
Crawl từ [sustainabilityreports.com/country/vietnam](https://www.sustainabilityreports.com/country/vietnam)

### Quy mô

| Metric | Giá trị |
|--------|---------|
| Tổng số công ty | **309** |
| Tổng báo cáo (API) | **867** |
| Báo cáo đã fetch | **855** |
| PDFs đã tải | **823** |
| Khoảng thời gian | ~2006 – 2025 |
| Dung lượng PDF | 400KB – 430MB |

### Cấu trúc dữ liệu hiện có

```
data/vietnam_sustainabilityreports/
├── manifest.json          ← metadata crawl
├── vietnam_companies.json ← 309 công ty (company_key, name, ticker, ISIN, sector, slug, report_count)
├── vietnam_reports.json   ← 855 báo cáo (report_id, year, type, lang, title, pages, filesize, pdf_url)
└── pdfs/                  ← 823 file PDF
    └── {company-slug}_{year}_{type}_{report_id}.pdf

data/esg100_top100_2025.csv  ← Bảng xếp hạng ESG100 Top 100 VN 2025
```

---

## 2. Các Fields Có Sẵn & Đánh Giá

### 2.1 [vietnam_companies.json](file:///d:/Github/RG_Greenwashing/data/vietnam_sustainabilityreports/vietnam_companies.json) — Metadata công ty

| Field | Ý nghĩa | Đánh giá |
|-------|---------|----------|
| `company_key` | Mã sàn + ticker (VD: `XSTC_DHG`) | ✅ **Lấy** — dùng làm primary key |
| `company_name` | Tên tiếng Anh | ✅ **Lấy** |
| `company_ticker` | Mã chứng khoán | ✅ **Lấy** — join với dữ liệu tài chính |
| `company_isin` | Mã ISIN quốc tế | ⚠️ **Tùy chọn** — có null, chỉ cần nếu join data quốc tế |
| `company_country` | Luôn = "Vietnam" | ❌ **Bỏ** — không có giá trị phân biệt |
| `company_sector` | Ngành (VD: Health Care, Financials) | ✅ **Lấy** — quan trọng cho phân tích theo ngành |
| `company_slug` | URL-safe name | ✅ **Lấy** — mapping với tên PDF |
| `report_count` | Số báo cáo có trên hệ thống | ✅ **Lấy** — metric về mức độ minh bạch |
| `latest_report_year` | Năm báo cáo mới nhất | ✅ **Lấy** — đánh giá tính cập nhật |

### 2.2 [vietnam_reports.json](file:///d:/Github/RG_Greenwashing/data/vietnam_sustainabilityreports/vietnam_reports.json) — Metadata báo cáo

| Field | Ý nghĩa | Đánh giá |
|-------|---------|----------|
| `company_name` | Tên công ty | ✅ **Lấy** — join key |
| `company_slug` | Slug | ✅ **Lấy** — mapping PDF filename |
| `company_isin` | ISIN | ⚠️ Tùy chọn |
| `report_id` | ID báo cáo | ✅ **Lấy** — unique key per report |
| `report_year` | Năm báo cáo | ✅ **Lấy** — phân tích time-series |
| `report_type` | Loại: SR, AR, AR+, IR | ✅ **RẤT QUAN TRỌNG** — xem giải thích bên dưới |
| `report_lang` | Ngôn ngữ (EN/VI) | ✅ **Lấy** — filter cho NLP pipeline |
| `report_title` | Tiêu đề | ✅ **Lấy** — thông tin bổ sung |
| `report_pages` | Số trang | ✅ **Lấy** — proxy cho mức độ chi tiết |
| `report_filesize_mb` | Dung lượng file (MB) | ⚠️ Tùy chọn — ít giá trị phân tích |
| `pdf_url` | URL download | ✅ **Lấy** — truy xuất nguồn |
| `download_error` | Lỗi download (nếu có) | ⚠️ Dùng để lọc, rồi bỏ |

### 2.3 Giải thích Report Types

| Type | Nghĩa | Giá trị cho nghiên cứu Greenwashing |
|------|--------|--------------------------------------|
| **SR** | Sustainability Report | ⭐⭐⭐ **Cao nhất** — nội dung ESG thuần túy |
| **AR+** | Annual Report (tích hợp ESG) | ⭐⭐ Cao — có section ESG trong báo cáo thường niên |
| **IR** | Integrated Report | ⭐⭐⭐ Cao — tích hợp tài chính + ESG |
| **AR** | Annual Report (thuần tài chính) | ⭐ Thấp — chủ yếu là báo cáo tài chính, ít ESG |

---

## 3. Đề Xuất Ứng Dụng Dữ Liệu

### 3.1 🔬 Phát hiện Greenwashing (Mục tiêu chính dự án)

**Ý tưởng**: So sánh "lời nói" (trong báo cáo SR) vs "hành động thực tế" (dữ liệu tài chính/ESG bên ngoài).

**Phương pháp**:
1. **Text mining** từ PDF → trích xuất cam kết ESG (emissions, energy, waste, diversity...)
2. **Sentiment/tone analysis** — đo mức độ "positive spin" vs nội dung cụ thể
3. **Vagueness score** — đo tỷ lệ cam kết chung chung vs cam kết cụ thể (có số liệu)
4. **Cross-reference** với dữ liệu thực tế (nếu có) hoặc ESG100 ranking

### 3.2 📊 Phân tích Xu hướng ESG Reporting ở Việt Nam

- **Trend over time**: Số lượng + chất lượng báo cáo SR qua các năm
- **Sector comparison**: Ngành nào báo cáo nhiều/tốt nhất?
- **Report sophistication**: Số trang, loại báo cáo, ngôn ngữ theo thời gian
- **Early adopters vs Late adopters**: Ai bắt đầu báo cáo sớm nhất?

### 3.3 🏆 Đối chiếu với ESG100 Ranking

Bạn đã có file [esg100_top100_2025.csv](file:///d:/Github/RG_Greenwashing/data/esg100_top100_2025.csv) (100 công ty hàng đầu ESG). Có thể:
- Map ticker/tên DN giữa 2 nguồn dữ liệu
- So sánh: DN có thứ hạng ESG100 cao có báo cáo SR nhiều/tốt hơn không?
- Tìm contradictions: DN ranking cao nhưng nội dung SR mờ nhạt = **greenwashing candidate**

### 3.4 📝 NLP / Text Analysis trên nội dung PDF

**Từ nội dung PDF, có thể trích xuất**:
- GRI Standards disclosure (GRI 302, 305, 306...)
- SDGs được nhắc đến
- Cam kết Net-Zero / Carbon Neutral
- Số liệu định lượng (tấn CO₂, KWh, % nữ lãnh đạo...)
- So sánh cùng công ty qua nhiều năm

---

## 4. Đề Xuất Processing Pipeline

### Phase 1: Data Cleaning & Structuring

```
1. Merge vietnam_companies.json + vietnam_reports.json → companies_reports.csv
2. Lọc bỏ báo cáo có download_error
3. Map PDF filename → report metadata
4. Phân loại: SR/IR (ưu tiên cao) vs AR/AR+ (ưu tiên thấp)
5. Join với esg100_top100_2025.csv bằng ticker/tên DN
```

### Phase 2: PDF Text Extraction

```
1. Extract text từ PDF (dùng pdfplumber / PyMuPDF)
2. Lưu text vào DB/file (.txt hoặc .json per report)
3. Detect ngôn ngữ và lọc → chỉ giữ EN (hoặc xử lý VI riêng)
4. Xử lý OCR cho PDF dạng scan (nếu có)
```

### Phase 3: Feature Extraction từ Text

| Feature | Cách trích xuất | Mục đích |
|---------|-----------------|----------|
| **GRI Index** | Regex/keyword search "GRI 3xx" | Mức độ tuân thủ chuẩn quốc tế |
| **SDG mentions** | Keyword matching SDG 1-17 | Cam kết phát triển bền vững |
| **Quantitative metrics** | NER + regex (số + đơn vị) | Có cam kết cụ thể không? |
| **Vagueness indicators** | Count vague words ("strive", "aim", "commit") vs specific ("reduced by 15%") | Chỉ số greenwashing |
| **ESG topic coverage** | Topic modeling (LDA/BERTopic) | Chủ đề nào được nhấn mạnh? |
| **Sentiment** | Sentiment model | Tone quá tích cực = đáng ngờ |
| **Year-over-year change** | Diff text giữa 2 năm cùng công ty | Có tiến bộ thực sự không? |

### Phase 4: Analysis & Scoring

```
1. Greenwashing Score per company (dựa trên features trên)
2. Sector-level analysis
3. Temporal analysis (improvement over time?)
4. Correlation với ESG100 ranking
5. Visualization & Dashboard
```

---

## 5. Đề Xuất Lọc Dữ Liệu — Giữ vs Bỏ

### ✅ NÊN GIỮ (ưu tiên xử lý)

| Tiêu chí | Lý do |
|-----------|-------|
| Report type = **SR** hoặc **IR** | Nội dung ESG chuyên sâu nhất |
| Năm **2018–2024** | Giai đoạn ESG reporting phát triển mạnh ở VN |
| Ngôn ngữ **EN** | Dễ xử lý NLP, tools nhiều hơn |
| Công ty có **≥ 3 báo cáo SR/IR** | Đủ data cho time-series analysis |
| Công ty trong **ESG100** | Có điểm so sánh benchmark |

### ⚠️ TÙY CHỌN

| Tiêu chí | Lý do |
|-----------|-------|
| Report type = **AR+** | Có ESG content nhưng lẫn trong báo cáo tài chính |
| Năm **2014–2017** | Dữ liệu sớm, useful cho trend nhưng ít chi tiết |
| Ngôn ngữ **VI** | Cần thêm bước dịch/NLP tiếng Việt |

### ❌ NÊN BỎ (hoặc deprioritize)

| Tiêu chí | Lý do |
|-----------|-------|
| Report type = **AR** (thuần tài chính) | Gần như không có nội dung ESG |
| Có `download_error` | File không tải được |
| Năm **trước 2014** | Quá cũ, ít relevance |
| File > 100MB | Nhiều hình ảnh, ít text hữu ích (tỷ lệ noise cao) |
| Công ty chỉ có **1 báo cáo** | Không đủ data cho pattern analysis |
| Field `company_country` | Luôn = "Vietnam", không có giá trị |

---

## 6. Câu Hỏi Cần Làm Rõ Trước Khi Tiến Hành

> [!IMPORTANT]
> Tôi cần xác nhận một số điểm trước khi đề xuất implementation plan chi tiết:

1. **Mục tiêu chính** của bạn là gì?
   - (a) Phát hiện Greenwashing (so sánh lời nói vs hành động)?
   - (b) Phân tích xu hướng ESG reporting ở VN?
   - (c) Xếp hạng/đánh giá chất lượng báo cáo?
   - (d) Một mục tiêu khác?

2. **Bạn có nguồn dữ liệu "ground truth" nào không?** (VD: dữ liệu phát thải thực tế, vi phạm môi trường, kết quả kiểm toán ESG...) — Cần để so sánh "lời nói" vs "thực tế".

3. **Đây là cho nghiên cứu học thuật hay ứng dụng thực tế?** — Ảnh hưởng đến phương pháp và mức độ chi tiết.

4. **Bạn muốn xử lý bao nhiêu PDFs?** Toàn bộ 823 file hay chỉ subset (VD: chỉ SR/IR, chỉ ESG100 companies)?

5. **Bạn có budget cho AI/LLM APIs không?** (VD: GPT-4 để trích xuất thông tin từ PDF sẽ hiệu quả hơn regex nhưng tốn chi phí).

6. **File [esg100_top100_2025.csv](file:///d:/Github/RG_Greenwashing/data/esg100_top100_2025.csv)** — Cột "Tình trạng" (DONE/trống) nghĩa là gì?
