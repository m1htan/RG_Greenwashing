"""
Crawl all Vietnam companies and sustainability/annual reports from SustainabilityReports.com.

The site is behind Cloudflare; direct HTTP to the backend API returns access_denied.
This script uses nodriver (undetected Chromium) to load the site origin, then performs
synchronous XHR from the page context — the same mechanism the Next.js app uses.

Public API (discovered from network traffic):
  GET .../api/public/taxonomy/country/vietnam/companies?page=&per_page=
  GET .../api/public/reports?page=&per_page=&isins=<ISIN>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import nodriver as uc
from nodriver.cdp.runtime import ExceptionDetails

LOG = logging.getLogger("vietnam_sustainability_crawl")

# Base URL observed in browser network (Azure Functions). Update if the site changes hosts.
DEFAULT_API_BASE = (
    "https://srdp-api-gah6f2asbedwagbp.westeurope-01.azurewebsites.net"
)
ORIGIN_PAGE = "https://www.sustainabilityreports.com/country/vietnam"


def _configure_logging(level: int, log_file: Path | None) -> None:
    """Chỉ logger của script dùng --log-level; nodriver/asyncio giữ WARNING để không spam DEBUG."""
    logging.getLogger().setLevel(logging.WARNING)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    LOG.setLevel(level)
    LOG.handlers.clear()
    LOG.propagate = False
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(fmt)
    LOG.addHandler(h)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        LOG.addHandler(fh)


async def _xhr_get_json(tab: uc.Tab, url: str, *, context: str) -> dict:
    """Run sync XHR in page context; returns parsed JSON."""
    LOG.debug("XHR bắt đầu [%s] URL=%s", context, url)
    js = (
        "(function(){var u="
        + json.dumps(url)
        + ";var x=new XMLHttpRequest();"
        "x.open('GET',u,false);x.send();"
        "return x.responseText;})()"
    )
    raw = await tab.evaluate(js, return_by_value=True)
    if isinstance(raw, ExceptionDetails):
        LOG.error(
            "XHR thất bại [%s]: lỗi JavaScript trong trang — %s",
            context,
            raw.text,
        )
        raise RuntimeError(f"JS error: {raw.text}")
    if not raw:
        LOG.error("XHR thất bại [%s]: response rỗng", context)
        raise RuntimeError("empty XHR response")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        preview = raw[:500] if isinstance(raw, str) else str(raw)[:500]
        LOG.exception(
            "XHR [%s]: không parse được JSON. 500 ký tự đầu response: %r",
            context,
            preview,
        )
        raise
    LOG.debug("XHR xong [%s]: keys=%s", context, list(data.keys()) if isinstance(data, dict) else type(data))
    return data


def _safe_filename(s: str) -> str:
    s = re.sub(r'[<>:"/\\|?*]', "_", s)
    return s.strip()[:180] or "file"


async def _run(
    api_base: str,
    out_dir: Path,
    download_pdfs: bool,
    skip_existing: bool,
    per_page_companies: int,
    per_page_reports: int,
    headless: bool,
    max_companies: int | None,
) -> None:
    LOG.info("=== Bước 1: Chuẩn bị thư mục đầu ra ===")
    LOG.info("Thư mục: %s", out_dir.resolve())
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir = out_dir / "pdfs"
    if download_pdfs:
        pdf_dir.mkdir(parents=True, exist_ok=True)
        LOG.info("Đã bật tải PDF → %s", pdf_dir.resolve())
    else:
        LOG.info("Không tải PDF (chỉ metadata JSON)")

    browser = None
    try:
        LOG.info("=== Bước 2: Khởi động trình duyệt (nodriver) ===")
        LOG.info("headless=%s", headless)
        browser = await uc.start(headless=headless)
        LOG.info("Trình duyệt đã sẵn sàng")

        tab = browser.main_tab
        LOG.info("=== Bước 3: Tải trang gốc (vượt Cloudflare / session) ===")
        LOG.info("Đang mở: %s", ORIGIN_PAGE)
        await tab.get(ORIGIN_PAGE)
        LOG.info("Chờ 15s để trang và script ổn định…")
        await tab.sleep(15)
        LOG.info("Trang gốc xong, bắt đầu gọi API qua XHR trong trang")

        companies_out: list[dict] = []
        reports_flat: list[dict] = []
        page_num = 1
        total_companies = None
        total_reports_site = None

        LOG.info("=== Bước 4: Lấy danh sách công ty Việt Nam (phân trang) ===")
        while True:
            u = (
                f"{api_base}/api/public/taxonomy/country/vietnam/companies"
                f"?page={page_num}&per_page={per_page_companies}"
            )
            LOG.info(
                "Gọi API companies: page=%s per_page=%s (đã có %s công ty)",
                page_num,
                per_page_companies,
                len(companies_out),
            )
            data = await _xhr_get_json(tab, u, context=f"companies page={page_num}")
            total_companies = data.get("total")
            if total_reports_site is None:
                total_reports_site = data.get("total_reports")
                LOG.info(
                    "API báo total công ty=%s, total_reports (site)=%s",
                    total_companies,
                    total_reports_site,
                )
            batch = data.get("companies") or []
            if not batch:
                LOG.warning("Trang companies page=%s trả về 0 công ty — kết thúc vòng lặp", page_num)
                break
            companies_out.extend(batch)
            LOG.info(
                "Trang %s: +%s công ty (tổng tích lũy %s / %s)",
                page_num,
                len(batch),
                len(companies_out),
                total_companies,
            )
            if len(companies_out) >= (total_companies or 0):
                LOG.info("Đã đủ số công ty theo total=%s", total_companies)
                break
            page_num += 1

        if max_companies is not None:
            before = len(companies_out)
            companies_out = companies_out[: max_companies]
            LOG.info(
                "Giới hạn --max-companies=%s: %s → %s công ty",
                max_companies,
                before,
                len(companies_out),
            )

        LOG.info("=== Bước 5: Với từng công ty — lấy báo cáo (và PDF nếu bật) ===")
        for i, co in enumerate(companies_out):
            isin = co.get("company_isin")
            slug = co.get("company_slug")
            name = co.get("company_name")
            if not isin:
                LOG.warning(
                    "Bỏ qua bản ghi không có company_isin: %s",
                    co,
                )
                continue

            LOG.info(
                "[%s/%s] Công ty: %s | ISIN=%s | slug=%s",
                i + 1,
                len(companies_out),
                name,
                isin,
                slug,
            )

            rpage = 1
            while True:
                ru = (
                    f"{api_base}/api/public/reports"
                    f"?page={rpage}&per_page={per_page_reports}&isins={quote(isin, safe='')}"
                )
                LOG.debug("Reports API: ISIN=%s page=%s", isin, rpage)
                rdata = await _xhr_get_json(
                    tab, ru, context=f"reports isin={isin} page={rpage}"
                )
                items = rdata.get("items") or []
                total_r = rdata.get("total")
                LOG.info(
                    "  → Trang báo cáo %s: %s mục (API total=%s)",
                    rpage,
                    len(items),
                    total_r,
                )
                for it in items:
                    row = {
                        "company_name": name,
                        "company_slug": slug,
                        "company_isin": isin,
                        "report_id": it.get("report_id"),
                        "report_year": it.get("report_year"),
                        "report_type": it.get("report_type"),
                        "report_lang": it.get("report_lang"),
                        "report_title": it.get("report_title"),
                        "report_pages": it.get("report_pages"),
                        "report_filesize_mb": it.get("report_filesize"),
                        "pdf_url": it.get("report_location"),
                    }
                    reports_flat.append(row)

                    if download_pdfs and it.get("report_location"):
                        fn = (
                            f"{_safe_filename(slug or 'company')}_"
                            f"{it.get('report_year')}_"
                            f"{_safe_filename(it.get('report_type') or 'rep')}_"
                            f"{it.get('report_id')}.pdf"
                        )
                        dest = pdf_dir / fn
                        if skip_existing and dest.exists():
                            LOG.debug("  Bỏ qua PDF đã có: %s", dest.name)
                            continue
                        LOG.info(
                            "  Tải PDF report_id=%s năm=%s → %s",
                            it.get("report_id"),
                            it.get("report_year"),
                            dest.name,
                        )
                        try:
                            req = Request(
                                it["report_location"],
                                headers={"User-Agent": "Mozilla/5.0 (compatible; RG_Greenwashing/1.0)"},
                            )
                            with urlopen(req, timeout=120) as resp:
                                body = resp.read()
                            dest.write_bytes(body)
                            LOG.info("  Đã lưu %s (%s bytes)", dest.name, len(body))
                        except HTTPError as ex:
                            row["download_error"] = str(ex)
                            LOG.error(
                                "  Lỗi HTTP khi tải PDF report_id=%s: %s",
                                it.get("report_id"),
                                ex,
                                exc_info=True,
                            )
                        except URLError as ex:
                            row["download_error"] = str(ex)
                            LOG.error(
                                "  Lỗi URL/network khi tải PDF report_id=%s: %s",
                                it.get("report_id"),
                                ex,
                                exc_info=True,
                            )
                        except OSError as ex:
                            row["download_error"] = str(ex)
                            LOG.error(
                                "  Lỗi ghi file PDF report_id=%s: %s",
                                it.get("report_id"),
                                ex,
                                exc_info=True,
                            )
                        except Exception as ex:
                            row["download_error"] = str(ex)
                            LOG.exception(
                                "  Lỗi không mong đợi khi tải PDF report_id=%s",
                                it.get("report_id"),
                            )

                if not items:
                    break
                per = rdata.get("per_page") or per_page_reports
                if total_r is not None and rpage * per >= total_r:
                    LOG.debug("  Hết báo cáo: rpage*per >= total_r")
                    break
                if len(items) < per:
                    LOG.debug("  Hết báo cáo: items < per_page")
                    break
                rpage += 1

        LOG.info("=== Bước 6: Ghi file JSON ===")
        manifest = {
            "source": ORIGIN_PAGE,
            "api_base": api_base,
            "total_companies_expected": total_companies,
            "total_reports_api": total_reports_site,
            "companies_fetched": len(companies_out),
            "reports_rows": len(reports_flat),
        }
        paths = {
            "companies": out_dir / "vietnam_companies.json",
            "reports": out_dir / "vietnam_reports.json",
            "manifest": out_dir / "manifest.json",
        }
        paths["companies"].write_text(
            json.dumps(companies_out, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        LOG.info("Đã ghi %s", paths["companies"])
        paths["reports"].write_text(
            json.dumps(reports_flat, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        LOG.info("Đã ghi %s", paths["reports"])
        paths["manifest"].write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        LOG.info("Đã ghi %s", paths["manifest"])

        LOG.info("=== Hoàn tất ===")
        LOG.info("Manifest: %s", json.dumps(manifest, ensure_ascii=False))
    except Exception:
        LOG.exception("Lỗi không xử lý được — xem traceback bên dưới để sửa cấu hình hoặc mạng")
        raise
    finally:
        if browser is not None:
            LOG.info("=== Đóng trình duyệt ===")
            try:
                browser.stop()
            except Exception:
                LOG.exception("Lỗi khi đóng trình duyệt (có thể bỏ qua nếu process đã thoát)")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    repo = Path(__file__).resolve().parent.parent
    rs = str(repo)
    if rs not in sys.path:
        sys.path.insert(0, rs)
    from config.settings import (
        get_bool,
        get_int,
        get_int_optional,
        get_path,
        get_path_optional,
        get_str,
        load_env,
    )

    load_env()

    p = argparse.ArgumentParser(
        description="Crawl Vietnam sustainability reports (SustainabilityReports.com).",
        epilog="Giá trị mặc định từ config/.env — xem config/.env.example.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=get_path("CRAWL_OUT_DIR", "data/vietnam_sustainabilityreports"),
        help="Output directory for JSON and optional PDFs",
    )
    p.add_argument(
        "--api-base",
        default=get_str("CRAWL_API_BASE", DEFAULT_API_BASE),
        help="Backend API base URL",
    )
    p.add_argument(
        "--download-pdfs",
        action=argparse.BooleanOptionalAction,
        default=get_bool("CRAWL_DOWNLOAD_PDFS", False),
        help="Download PDFs to out/pdfs",
    )
    p.add_argument(
        "--skip-existing",
        action=argparse.BooleanOptionalAction,
        default=get_bool("CRAWL_SKIP_EXISTING_PDFS", False),
        help="Skip PDFs that already exist on disk",
    )
    p.add_argument(
        "--per-page-companies",
        type=int,
        default=get_int("CRAWL_PER_PAGE_COMPANIES", 200),
    )
    p.add_argument(
        "--per-page-reports",
        type=int,
        default=get_int("CRAWL_PER_PAGE_REPORTS", 50),
    )
    p.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=get_bool("CRAWL_HEADLESS", False),
        help="Run Chromium headless (may affect Cloudflare)",
    )
    p.add_argument(
        "--max-companies",
        type=int,
        default=get_int_optional("CRAWL_MAX_COMPANIES"),
        help="Limit companies (debug)",
    )
    p.add_argument(
        "--log-level",
        default=get_str("CRAWL_LOG_LEVEL", "INFO"),
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Mức log (DEBUG = chi tiết API/phân trang)",
    )
    p.add_argument(
        "--log-file",
        type=Path,
        default=get_path_optional("CRAWL_LOG_FILE"),
        help="Ghi thêm log vào file UTF-8 (song song với stderr)",
    )
    args = p.parse_args()

    _configure_logging(getattr(logging, args.log_level), args.log_file)
    LOG.info("Khởi động crawl | log_level=%s", args.log_level)
    if args.log_file:
        LOG.info("Ghi log ra file: %s", args.log_file.resolve())

    asyncio.run(
        _run(
            api_base=args.api_base.rstrip("/"),
            out_dir=args.out,
            download_pdfs=args.download_pdfs,
            skip_existing=args.skip_existing,
            per_page_companies=args.per_page_companies,
            per_page_reports=args.per_page_reports,
            headless=args.headless,
            max_companies=args.max_companies,
        )
    )


if __name__ == "__main__":
    main()
