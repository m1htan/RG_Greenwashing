# Phân Tích Fields Bên Trong Các File PDF Sustainability Reports

> [!NOTE]
> Tôi đã trích xuất text từ **5 báo cáo SR** (PNJ, Bamboo Capital, FPT, SSI, Mobile World — năm 2023-2024) bằng PyMuPDF để phân tích cấu trúc nội dung bên trong. Dưới đây là kết quả chi tiết.

---

## 1. Tổng quan nội dung bên trong mỗi PDF

Mỗi file PDF Sustainability Report thường chứa các **nhóm thông tin** sau:

| # | Nhóm thông tin | Mô tả | Có ở tất cả SR? |
|---|---------------|-------|:---:|
| 1 | **Report Overview** | Tên công ty, năm báo cáo, phạm vi, phương pháp | ✅ |
| 2 | **CEO/Chairman Message** | Thông điệp của lãnh đạo | ✅ |
| 3 | **Company Profile** | Giới thiệu, lịch sử, sản phẩm, cơ cấu tổ chức | ✅ |
| 4 | **Governance (Quản trị)** | Cấu trúc quản trị ESG, hội đồng, ủy ban | ✅ |
| 5 | **Stakeholder Engagement** | Bản đồ bên liên quan, kênh tương tác | ✅ |
| 6 | **Materiality Assessment** | Ma trận trọng yếu, vấn đề ESG ưu tiên | ✅ |
| 7 | **Environmental (E)** | Phát thải GHG, năng lượng, nước, chất thải, đa dạng sinh học | ✅ |
| 8 | **Social (S)** | Nhân sự, đào tạo, an toàn lao động, cộng đồng | ✅ |
| 9 | **Governance (G)** | Chống tham nhũng, minh bạch, quản lý rủi ro | ✅ |
| 10 | **GRI Content Index** | Bảng tham chiếu GRI Standards | 4/5 |
| 11 | **Data Sheets / Appendices** | Bảng số liệu chi tiết (kWh, tCO2e, m³, %) | ✅ |
| 12 | **External Assurance** | Kiểm toán/xác nhận độc lập | 2/5 |

---

## 2. Các Fields Cụ Thể Có Thể Trích Xuất — Đánh Giá Chi Tiết

### 2.1 ⭐ ENVIRONMENTAL — Nhóm Môi Trường

| Field | Mô tả | Ví dụ thực tế trích được | Nên lấy? | Lý do |
|-------|--------|--------------------------|:---:|--------|
| **GHG Emissions (Scope 1, 2, 3)** | Phát thải khí nhà kính theo 3 phạm vi | BCG: `781,282,986 tCO2` | ✅ **LẤY** | Chỉ số cốt lõi cho greenwashing — so sánh cam kết vs thực tế |
| **Energy Consumption** | Tổng tiêu thụ năng lượng | PNJ: `4,688,883 kWh`, `19,934,531 kWh` | ✅ **LẤY** | Tracking hiệu quả năng lượng qua các năm |
| **Renewable Energy %** | Tỷ lệ năng lượng tái tạo | Phát hiện qua keyword `renewable energy` (BCG: 70 mentions) | ✅ **LẤY** | Đo cam kết chuyển đổi năng lượng |
| **Water Consumption** | Lượng nước sử dụng | FPT: `669,383 m³`; MWG: `1,155,751 m³` | ✅ **LẤY** | Quản lý tài nguyên nước |
| **Waste Management** | Chất thải (tổng, tái chế, nguy hại) | PNJ: 56 mentions "waste" | ✅ **LẤY** | Kinh tế tuần hoàn |
| **Biodiversity** | Đa dạng sinh học, hệ sinh thái | BCG: 38 mentions; PNJ: 8 mentions | ⚠️ **TÙY** | Chỉ quan trọng với một số ngành (nông nghiệp, khai khoáng) |

### 2.2 ⭐ SOCIAL — Nhóm Xã Hội

| Field | Mô tả | Ví dụ thực tế | Nên lấy? | Lý do |
|-------|--------|--------------|:---:|--------|
| **Total Employees** | Tổng số nhân viên | Trích được từ section "Human Capital" | ✅ **LẤY** | Baseline cho các chỉ số per-capita |
| **Training Hours** | Giờ đào tạo | PNJ: `58.5 hours/person`; SSI: `68,000 training hours`; FPT: `59,000 training hours` | ✅ **LẤY** | Đầu tư vào phát triển nhân lực |
| **Gender Diversity** | Tỷ lệ nam/nữ, nữ lãnh đạo | PNJ: 45 mentions "diversity/inclusion/gender" | ✅ **LẤY** | Chỉ số D&I quan trọng |
| **Occupational Safety** | Tỷ lệ tai nạn, LTIFR | Phát hiện keyword OHS/accident ở tất cả SR | ✅ **LẤY** | An toàn lao động |
| **Community Investment** | Đầu tư cộng đồng (VND) | FPT: `205.2 Billion VND`; MWG: CSR 91 mentions | ✅ **LẤY** | Trách nhiệm xã hội |
| **Human Rights** | Lao động trẻ em, cưỡng bức | SSI: 46 mentions | ⚠️ **TÙY** | Quan trọng cho supply chain |
| **Customer Privacy** | Bảo mật dữ liệu khách hàng | PNJ có section riêng | ⚠️ **TÙY** | Quan trọng cho ngành tài chính, bán lẻ |

### 2.3 ⭐ GOVERNANCE — Nhóm Quản Trị

| Field | Mô tả | Ví dụ | Nên lấy? | Lý do |
|-------|--------|-------|:---:|--------|
| **Anti-corruption** | Chính sách chống tham nhũng | PNJ: 9 mentions; SSI: 25 mentions | ✅ **LẤY** | Minh bạch quản trị |
| **Board Structure** | Cấu trúc HĐQT, thành viên độc lập | MWG: 113 mentions "governance" | ✅ **LẤY** | Chất lượng quản trị |
| **Risk Management** | Quản lý rủi ro ESG | PNJ có "Risk Management" section | ✅ **LẤY** | Năng lực quản lý rủi ro |
| **Tax Transparency** | Minh bạch thuế | PNJ có GRI 207 (Tax) | ⚠️ **TÙY** | Chỉ một số DN công bố |
| **Supply Chain Assessment** | Đánh giá nhà cung cấp ESG | MWG: 22 mentions "supply chain" | ✅ **LẤY** | Trách nhiệm chuỗi cung ứng |

### 2.4 ⭐ FRAMEWORKS & STANDARDS — Chuẩn mực

| Field | Phát hiện từ PDF | Nên lấy? | Lý do |
|-------|------------------|:---:|--------|
| **GRI Standards** | PNJ: 31 GRI codes (201-418); BCG: 31; SSI: 26; MWG: 20. **FPT: 0** | ✅ **LẤY** | Mức độ tuân thủ chuẩn quốc tế — cực kỳ quan trọng |
| **TCFD** | BCG ✅, SSI ✅, MWG ✅ | ✅ **LẤY** | Cam kết khí hậu |
| **ISSB** | BCG ✅, SSI ✅ | ✅ **LẤY** | Framework mới, cho thấy DN đi đầu |
| **SDGs** | MWG: 12 SDGs (1,3,4,5,6,7,8,9,12,13,16,17). PNJ/BCG/FPT/SSI: 0 | ✅ **LẤY** | Cam kết phát triển bền vững |
| **UN Global Compact** | MWG ✅ | ✅ **LẤY** | Cam kết quốc tế |
| **ISO 14001** | PNJ ✅, FPT ✅ | ✅ **LẤY** | Chứng nhận hệ thống quản lý môi trường |
| **External Assurance** | PNJ: PwC; MWG: Third-party verification. BCG/FPT/SSI: ❌ | ✅ **LẤY** | Có kiểm toán độc lập = đáng tin hơn |

### 2.5 📊 DỮ LIỆU ĐỊNH LƯỢNG (Percentages, Amounts)

| Field | Ví dụ | Nên lấy? | Lý do |
|-------|-------|:---:|--------|
| **Tỷ lệ %** | PNJ: 79 con số %; SSI: 153; BCG: 141 | ✅ **LẤY** | Cho thấy mức độ cụ thể vs chung chung |
| **Số liệu tài chính (VND/USD)** | FPT: `8,167 Billion VND`; SSI: `500 billion VND` | ⚠️ **TÙY** | Chỉ lấy nếu liên quan ESG (VD: đầu tư CSR) |
| **Số trang (report_pages)** | PNJ: 69 pages; MWG: ~100+ pages | ✅ **LẤY** | Proxy cho mức độ chi tiết |

---

## 3. Kết quả phân tích 5 mẫu PDF — So sánh

| Metric | PNJ 2024 SR | BCG 2024 SR | FPT 2023 SR | SSI 2024 SR | MWG 2024 SR |
|--------|:-----------:|:-----------:|:-----------:|:-----------:|:-----------:|
| Text extracted | 175K chars | 92K chars | 145K chars | 235K chars | 119K chars |
| GRI Codes | 31 ✅ | 31 ✅ | 0 ❌ | 26 ✅ | 20 ✅ |
| SDGs | ❌ | ❌ | ❌ | ❌ | 12 ✅ |
| Emissions mentions | 141 | 109 | 63 | 41 | 84 |
| Energy mentions | 43 | 70 | 23 | 25 | 25 |
| Water mentions | 40 | 10 | 8 | 9 | 4 |
| Waste mentions | 56 | 27 | 7 | 10 | 38 |
| Diversity mentions | 45 | 75 | 40 | 25 | 27 |
| Community mentions | 9 | 20 | 66 | 2 | 91 |
| Governance mentions | 66 | 7 | 10 | 36 | 113 |
| Quantitative data | kWh, VND, % | tCO2, kWh, VND, % | m³, VND, % | kWh, VND, % | m³, VND, % |
| External Assurance | PwC ✅ | ❌ | ❌ | ❌ | Third-party ✅ |
| Frameworks | GRI, ISO14001 | GRI, TCFD, ISSB | GRI, ISO14001 | GRI, TCFD, ISSB | GRI, TCFD, UNGC |

---

## 4. Đề Xuất: Lấy Gì, Bỏ Gì, Xử Lý Như Thế Nào

### ✅ CHẮC CHẮN LẤY — 15 fields ưu tiên cao

| # | Field | Cách trích xuất | Xử lý |
|---|-------|-----------------|-------|
| 1 | **GRI Standards Index** | Regex `GRI \d{3}` | Danh sách GRI codes → đếm coverage |
| 2 | **SDGs** | Regex `SDG \d{1,2}` | Danh sách SDGs → đếm |
| 3 | **GHG Emissions (tCO2e)** | Regex số + đơn vị `tCO2/tCO2e` | Parse số liệu, normalize đơn vị |
| 4 | **Energy (kWh/MWh/GJ)** | Regex số + đơn vị năng lượng | Parse, đổi sang cùng đơn vị |
| 5 | **Water (m³)** | Regex số + `m3/m³/cubic` | Parse |
| 6 | **Waste data** | Keyword + context extraction | Tổng chất thải, tỷ lệ tái chế |
| 7 | **Training hours** | Regex số + `training hours` | Parse |
| 8 | **Frameworks** | Keyword search (GRI/TCFD/SASB/ISSB/UNGC) | Boolean flags |
| 9 | **External Assurance** | Keyword search (PwC/KPMG/Deloitte/EY/assurance) | Boolean + tên đơn vị |
| 10 | **ESG topic mentions count** | Keyword count per topic (emissions, water, waste...) | Số lần nhắc → đo "focus areas" |
| 11 | **Vagueness Score** | Đếm từ mơ hồ ("aim to", "strive", "commit") vs cụ thể ("reduced by 15%") | Ratio → chỉ số greenwashing |
| 12 | **Quantitative Density** | Đếm số liệu cụ thể / tổng số trang | Cao = minh bạch; Thấp = có thể greenwashing |
| 13 | **Report language** | Detect EN/VI | Filter/route processing |
| 14 | **Total text extracted** | Toàn bộ text từ PDF | Input cho NLP / topic modeling |
| 15 | **Report type** | Từ filename | SR/IR ưu tiên cao |

### ⚠️ TÙY CHỌN — Lấy nếu có thời gian

| # | Field | Lý do tùy chọn |
|---|-------|-----------------|
| 16 | **Biodiversity mentions** | Chỉ relevant cho một số ngành |
| 17 | **Human Rights details** | Khó trích xuất chính xác |
| 18 | **Tax Transparency (GRI 207)** | Ít DN công bố |
| 19 | **CEO Message tone** | Cần sentiment analysis model |
| 20 | **Year-over-year targets** | Cần cross-reference nhiều năm cùng DN |

### ❌ KHÔNG NÊN LẤY — Noise cao, giá trị thấp

| # | Nội dung | Lý do bỏ |
|---|----------|----------|
| 1 | **Hình ảnh/đồ họa** | Không extract được text, chỉ tăng file size |
| 2 | **Bảng tài chính thuần (BCTC, CDKT, KQKD)** | Không liên quan ESG, đã có trong Annual Report |
| 3 | **Thông tin cổ đông, cổ phiếu** | Không liên quan ESG |
| 4 | **Headers, footers, page numbers** | Noise trong text extraction |
| 5 | **Phần giới thiệu chung (lịch sử, sản phẩm)** | Lặp lại mỗi năm, ít giá trị phân tích |
| 6 | **PDF metadata** (author, creator software) | Giá trị phân tích gần bằng 0 |

---

## 5. Đề Xuất Pipeline Xử Lý

```
PDF File
  │
  ▼
[1] Text Extraction (PyMuPDF/pdfplumber)
  │  → raw text per page
  ▼
[2] Language Detection + Filter
  │  → giữ EN, xử lý VI riêng nếu cần
  ▼
[3] Section Segmentation
  │  → tách theo chapter: Environment / Social / Governance
  ▼
[4] Field Extraction
  │  ├── Regex: GRI codes, SDGs, quantitative data
  │  ├── Keyword count: ESG topics, frameworks
  │  └── (Optional) LLM: trích xuất cam kết phức tạp
  ▼
[5] Scoring
  │  ├── GRI Coverage Score (bao nhiêu GRI?)
  │  ├── Quantitative Density Score (bao nhiêu số liệu / trang?)
  │  ├── Vagueness Score (mơ hồ vs cụ thể?)
  │  ├── Framework Compliance Score
  │  └── Assurance Score (có kiểm toán độc lập?)
  ▼
[6] Output: Structured CSV/JSON per company per year
```

---

## 6. Câu Hỏi Cần Xác Nhận

> [!IMPORTANT]
> Trước khi tôi bắt tay vào code, xin xác nhận:

1. **Bạn muốn tôi xử lý tất cả 823 PDFs hay chỉ một subset?** (VD: chỉ SR/IR, hoặc chỉ các công ty ESG100?)
2. **Bạn muốn output ở dạng nào?** (CSV, JSON, database SQLite, hay dashboard?)
3. **Bạn có muốn dùng LLM (GPT/Claude) để trích xuất thông tin phức tạp không?** Hay chỉ dùng regex/keyword (miễn phí nhưng kém chính xác hơn)?
4. **Mục tiêu cuối cùng** là gì — nghiên cứu greenwashing, scoring ESG, hay phân tích trend?
