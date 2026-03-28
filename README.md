# RG_Greenwashing

## Kiểm thử (smoke tests)

```bash
python -m unittest discover -s tests -v
```

Kiểm tra: `config.settings`, parse JSON, post-process claims, prompt placeholders, metadata `company_sector`, và `--help` của hai script (trên Windows stdout dùng UTF-8 để epilog tiếng Việt không lỗi).

## Cấu hình (`config/.env`)

- **Mẫu đầy đủ biến:** [`config/.env.example`](config/.env.example) — copy thành `config/.env` và điền giá trị (đặc biệt `GEMINI_API_KEY` hoặc `GOOGLE_API_KEY`). Script ưu tiên `GEMINI_API_KEY`; nếu trong `.env` có **cả hai** khóa, SDK từng in cảnh báo — code đã bọc `Client()` để giảm cảnh báo; tốt nhất chỉ giữ **một** khóa trong `.env`.
- **Thứ tự load:** `config/.env` trước, sau đó `.env` ở gốc repo (nếu có).
- **Model LLM** (Gemini) chỉ cấu hình qua biến `GEMINI_MODEL_PRO`, `GEMINI_MODEL_BATCH` trong `.env` (hoặc ghi đè bằng `--model-pro` / `--model-batch` khi chạy lệnh).
- **Đường dẫn crawl / CSV / PDF:** xem tiền tố `CRAWL_*` và `GEMINI_*` trong `config/.env.example`.

## Hướng dẫn chạy từng phần

Pipeline tổng quát: **(A) cài dependency** → **(B) crawl** (tuỳ chọn) lấy metadata + PDF → **(C) trích xuất** bằng Gemini ra CSV/JSONL. Bạn có thể bỏ qua (B) nếu đã có sẵn PDF và JSON (hoặc chỉ cần PDF, chấp nhận metadata thiếu).

### Một lần: cài gói Python

```bash
pip install -r requirements.txt
```

### Phần A — Chỉ kiểm thử (không crawl, không Gemini)

```bash
python -m unittest discover -s tests -v
```

### Phần B — Chỉ crawl (không trích xuất, không cần `GEMINI_API_KEY`)

Mục đích: tải danh sách báo cáo + công ty, và (tuỳ chọn) file PDF vào một thư mục.

- Chỉ metadata + manifest (không tải PDF):

```bash
python scripts/crawl_vietnam_sustainability_reports.py --out data/vietnam_sustainabilityreports
```

- Crawl và tải PDF (bỏ qua file đã có):

```bash
python scripts/crawl_vietnam_sustainability_reports.py --out data/vietnam_sustainabilityreports --download-pdfs --skip-existing
```

Đầu ra thường dùng cho bước sau: `vietnam_reports.json`, `vietnam_companies.json`, thư mục `pdfs/` (nếu bật tải). Đường dẫn mặc định trong `.env` trích xuất trỏ tới cấu trúc này — xem `GEMINI_*` trong [`config/.env.example`](config/.env.example).

### Phần C — Chỉ trích xuất (Gemini), **không** chạy crawl

Dùng khi bạn đã có PDF (và nên có hai file JSON crawl) và chỉ muốn gọi model.

**Cần có:**

1. **`GEMINI_API_KEY`** (hoặc `GOOGLE_API_KEY`) trong `config/.env` — xem [`config/.env.example`](config/.env.example).
2. Thư mục **`--pdf-dir`** chứa các file `.pdf` cần xử lý.
3. **Khuyến nghị:** `--reports-json` và `--companies-json` trỏ đúng `vietnam_reports.json` và `vietnam_companies.json` để điền tên công ty, `company_sector`, v.v. Nếu thiếu hoặc tên file PDF không khớp metadata, script vẫn chạy nhưng có cảnh báo và một số cột trống.

**Chạy theo mặc định trong `.env`** (đường dẫn PDF/JSON/CSV lấy từ biến `GEMINI_*`):

```bash
python scripts/extract_esg_fields.py
```

**Chạy chỉ định rõ đường dẫn** (ví dụ PDF nằm nơi khác):

```bash
python scripts/extract_esg_fields.py --pdf-dir path/to/pdfs --reports-json path/to/vietnam_reports.json --companies-json path/to/vietnam_companies.json --output data/esg_extracted.csv
```

**Chạy thử ít file** (debug, tiết kiệm quota):

```bash
python scripts/extract_esg_fields.py --max-files 2
```

**Tiếp tục sau khi dừng giữa chừng** (ghi thêm dòng mới, không ghi đè CSV; bỏ qua PDF đã có trong CSV):

```bash
python scripts/extract_esg_fields.py --skip-existing
```

**Xem đầy đủ tham số** (model, `max-claims`, JSONL, v.v.):

```bash
python scripts/extract_esg_fields.py --help
```

**Đầu ra:** CSV (mặc định `data/esg_extracted.csv`) và thường kèm file **JSONL** cùng tên base đổi `.jsonl` (trừ khi `GEMINI_WRITE_JSONL=false` hoặc `--no-jsonl`). Chi tiết cột và JSONL nằm ở mục *Trích xuất ESG* bên dưới.

### Tóm tắt nhanh

| Bạn muốn | Lệnh chính |
|----------|------------|
| Chỉ test code | `python -m unittest discover -s tests -v` |
| Chỉ crawl | `python scripts/crawl_vietnam_sustainability_reports.py --out ...` (thêm `--download-pdfs` nếu cần PDF) |
| Chỉ trích xuất | Đặt `GEMINI_API_KEY` trong `config/.env`, rồi `python scripts/extract_esg_fields.py` (và chỉnh `--pdf-dir` / JSON nếu cần) |

## Crawl Vietnam reports (SustainabilityReports.com)

Trang [country/vietnam](https://www.sustainabilityreports.com/country/vietnam) dùng Cloudflare; API backend chặn gọi trực tiếp từ `curl`/Python. Script mở Chromium (nodriver), tải trang gốc rồi gọi API giống trình duyệt (XHR đồng bộ trong trang).

```bash
pip install -r requirements.txt
python scripts/crawl_vietnam_sustainability_reports.py --out data/vietnam_sustainabilityreports
```

- Log theo từng bước ra **stderr**; `--log-level DEBUG` bật chi tiết XHR/phân trang (chỉ logger `vietnam_sustainability_crawl`, không bật DEBUG toàn cục cho nodriver). `--log-file path/to/crawl.log` ghi song song file UTF-8.
- Ghi `vietnam_companies.json`, `vietnam_reports.json`, `manifest.json` (metadata + số dòng báo cáo).
- Tùy chọn tải PDF: `--download-pdfs` (lưu vào `out/pdfs`; Azure Blob thường cho phép tải trực tiếp).

Số liệu trên UI (ví dụ 758 reports) có thể lệch so với trường `total_reports` trong API; `manifest.json` ghi `total_reports_api` để đối chiếu.

**Lưu ý:** Tuân thủ [Điều khoản](https://www.sustainabilityreports.com/) và robots của site; dữ liệu thuộc bên thứ ba.

Cách tải pdfs:

```bash
python scripts/crawl_vietnam_sustainability_reports.py --out data/vietnam_sustainabilityreports --download-pdfs --skip-existing
```

## Trích xuất ESG + vagueness + claim–evidence (Gemini)

**Biến môi trường:** xem `config/.env.example` (`GEMINI_*`). `GEMINI_API_KEY` bắt buộc trong `config/.env` (hoặc biến hệ thống).

**Chạy mặc định:** từ `.env`: `GEMINI_TEMPERATURE`, `GEMINI_MODEL_PRO`, `GEMINI_MODEL_BATCH`, `GEMINI_SAMPLE_PRO_N`, đường dẫn I/O. Có thể ghi đè bằng tham số CLI. Nếu API báo model không khả dụng, sửa `GEMINI_MODEL_BATCH` / `GEMINI_MODEL_PRO` hoặc cờ `--model-batch` / `--model-pro`.

**Metadata:** `company_sector` lấy từ `vietnam_companies.json` (trường `company_sector`).

**Đầu ra CSV** (`data/esg_extracted.csv` mặc định): các cột metric phẳng + `claims_json` (chuỗi JSON: danh sách claim, mỗi claim có `section_heading`, `evidence_lines` với `page` + `quote` ≤ N ký tự, nhiều dòng evidence/claim). Cột `extraction_status`: `ok` | `partial` | `parse_error` | `error`; `parse_error` ghi lý do ngắn. Cột bổ sung: `metadata_in_lookup`, `text_extraction_mode` (upload/local), cảnh báo trích xử lý local (`local_truncated`, `local_low_text_density`, `chars_per_page_avg`), và khi API trả lời rỗng: `api_finish_reason`, `prompt_block_reason`.

**JSONL** (mặc định bật, ghi file cùng base với CSV đổi `.jsonl`): mỗi dòng một object JSON (một báo cáo); trường `claims` là mảng (không phải chuỗi `claims_json`). Tắt: `GEMINI_WRITE_JSONL=false` hoặc `--no-jsonl`. Đường dẫn: `GEMINI_JSONL_OUTPUT` hoặc `--jsonl-output`.

**Prompt:** `config/esg_extraction_prompt.txt` — placeholder `{{MAX_CLAIMS}}`, `{{MAX_QUOTE_CHARS}}` được thay bởi `--max-claims` và `--max-quote-chars`.

**Khung gợi ý (để bạn tinh chỉnh trong luận):** đánh giá **độ mơ hồ theo từng claim** (`vagueness_piece`) và **khoảng cách claim–bằng chứng** (`claim_evidence_gap`) theo rubric vận hành trong prompt; không gắn một bài báo cụ thể — bạn có thể thay thế/đối chiếu khi đã chốt khung nghiên cứu.

```bash
pip install -r requirements.txt
python scripts/extract_esg_fields.py --pdf-dir data/vietnam_sustainabilityreports/pdfs --max-claims 10 --max-quote-chars 500 --sample-pro-n 5
```