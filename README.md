# RG_Greenwashing

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