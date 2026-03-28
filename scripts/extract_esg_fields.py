"""
Extract ESG metrics, vagueness, and claim–evidence structures from sustainability PDFs via Gemini API.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import time
from json import JSONDecoder
from pathlib import Path
from typing import Any, Optional

import fitz  # PyMuPDF
from google import genai
from google.genai import types

LOG = logging.getLogger("esg_extractor")

# Gemini Files API upload limit ~50MB; stay below to be safe.
MAX_UPLOAD_SIZE = 48 * 1024 * 1024
# Local text extraction: tail may be omitted for very long reports.
MAX_LOCAL_TEXT_CHARS = 800_000
DEFAULT_LOW_TEXT_CHARS_PER_PAGE = 80


def _ensure_repo_on_path() -> None:
    repo = Path(__file__).resolve().parent.parent
    rs = str(repo)
    if rs not in sys.path:
        sys.path.insert(0, rs)

FLAT_KEYS = [
    "gri_standards",
    "sdgs",
    "frameworks",
    "external_assurance",
    "ghg_scope1",
    "ghg_scope2",
    "ghg_scope3",
    "total_energy_consumption",
    "renewable_energy_pct",
    "water_consumption",
    "total_waste",
    "waste_recycled_pct",
    "total_employees",
    "female_employee_pct",
    "female_leadership_pct",
    "training_hours_per_employee",
    "ltifr",
    "community_investment",
    "has_net_zero_commitment",
    "net_zero_target_year",
    "key_esg_commitments",
    "vagueness_assessment",
    "quantitative_data_richness",
]


def _configure_logging(log_file: Optional[Path] = None) -> None:
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    LOG.setLevel(logging.INFO)
    LOG.handlers.clear()
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(fmt)
    LOG.addHandler(h)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        LOG.addHandler(fh)


def load_metadata(reports_json: Path, companies_json: Path) -> dict[str, dict]:
    """Map PDF filename -> report row enriched with company_sector from companies JSON."""
    if not reports_json.exists() or not companies_json.exists():
        LOG.warning("Metadata JSON files not found. Metadata columns may be empty.")
        return {}
    try:
        with open(reports_json, encoding="utf-8") as f:
            reports = json.load(f)
        with open(companies_json, encoding="utf-8") as f:
            companies = json.load(f)
        company_lookup = {c.get("company_isin", ""): c for c in companies if c.get("company_isin")}
        import re

        def safe_filename(s: str) -> str:
            return re.sub(r'[<>:"/\\|?*]', "_", str(s)).strip()[:180] or "file"

        lookup: dict[str, dict] = {}
        for r in reports:
            slug = r.get("company_slug", "company")
            year = r.get("report_year", "")
            rtype = r.get("report_type", "rep")
            rid = r.get("report_id", "")
            fn = f"{safe_filename(slug)}_{year}_{safe_filename(rtype)}_{rid}.pdf"
            isin = r.get("company_isin", "")
            c_info = company_lookup.get(isin, {})
            r = dict(r)
            r["company_ticker"] = c_info.get("company_ticker", "")
            r["company_sector"] = c_info.get("company_sector", "")
            lookup[fn] = r
        return lookup
    except Exception as e:
        LOG.error("Error loading metadata: %s", e)
        return {}


def extract_text_locally(
    pdf_path: Path, *, min_chars_per_page: int = DEFAULT_LOW_TEXT_CHARS_PER_PAGE
) -> tuple[str, dict[str, Any]]:
    """Extract text from oversized PDFs (PyMuPDF). Returns (text, diagnostics)."""
    LOG.info("Extracting text locally (oversized file): %s", pdf_path.name)
    diagnostics: dict[str, Any] = {
        "truncated": False,
        "page_count": 0,
        "chars_per_page_avg": 0.0,
        "low_text_density": False,
    }
    text_parts: list[str] = []
    try:
        doc = fitz.open(pdf_path)
        n_pages = len(doc)
        diagnostics["page_count"] = n_pages
        for page in doc:
            text_parts.append(page.get_text("text"))
            text_parts.append("\n")
        doc.close()
        text = "".join(text_parts)
        if len(text) > MAX_LOCAL_TEXT_CHARS:
            LOG.warning(
                "Text very large (%s chars): truncating to %s — tail of report omitted (metrics/claims near end may be missing).",
                len(text),
                MAX_LOCAL_TEXT_CHARS,
            )
            text = text[:MAX_LOCAL_TEXT_CHARS]
            diagnostics["truncated"] = True
        avg = len(text) / max(n_pages, 1)
        diagnostics["chars_per_page_avg"] = round(avg, 1)
        if avg < min_chars_per_page:
            diagnostics["low_text_density"] = True
            LOG.warning(
                "Low text density (%.1f chars/page < %s): possible scan-only or image-heavy PDF; model output may be unreliable.",
                avg,
                min_chars_per_page,
            )
        return text, diagnostics
    except Exception as e:
        LOG.error("Failed local text extraction: %s", e)
        return "", diagnostics


def parse_json_response(text: str) -> tuple[dict[str, Any], Optional[str]]:
    """Parse model JSON; return (obj, error_reason)."""
    if not text or not text.strip():
        return {}, "empty_response"
    text = text.strip()
    try:
        o = json.loads(text)
        if isinstance(o, dict):
            return o, None
        return {}, "root_not_object"
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start < 0:
        return {}, "no_json_object"
    decoder = JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(text, start)
        if isinstance(obj, dict):
            return obj, None
        return {}, "root_not_object"
    except json.JSONDecodeError as e:
        LOG.error("JSON parse error: %s | head: %r", e, text[:400])
        return {}, "json_decode_error"


def _coerce_bool(v: Any) -> bool | None:
    """Normalize LLM output to bool (handles 'true'/'false' strings)."""
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return bool(v)
    if isinstance(v, float):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "yes", "1", "on"):
            return True
        if s in ("false", "no", "0", "off", ""):
            return False
    return None


def _bool_to_csv(v: Any) -> str:
    b = _coerce_bool(v)
    if b is not None:
        return "true" if b else "false"
    if v is None:
        return ""
    return str(v)


def _response_debug(response: Any) -> dict[str, Any]:
    """Best-effort API debug when text is empty or for logging."""
    d: dict[str, Any] = {}
    try:
        pf = getattr(response, "prompt_feedback", None)
        if pf is not None:
            br = getattr(pf, "block_reason", None)
            if br is not None:
                d["prompt_block_reason"] = str(br)
        cands = getattr(response, "candidates", None) or []
        if cands:
            c0 = cands[0]
            fr = getattr(c0, "finish_reason", None)
            if fr is not None:
                d["finish_reason"] = str(fr)
            fm = getattr(c0, "finish_message", None)
            if fm:
                d["finish_message"] = str(fm)
        um = getattr(response, "usage_metadata", None)
        if um is not None:
            d["prompt_token_count"] = getattr(um, "prompt_token_count", None)
            d["candidates_token_count"] = getattr(um, "candidates_token_count", None)
    except Exception:
        pass
    return d


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as jf:
        jf.write(json.dumps(record, ensure_ascii=False) + "\n")


def row_to_jsonl_record(row: dict[str, Any]) -> dict[str, Any]:
    """CSV row → JSON object with `claims` as array."""
    out = dict(row)
    cj = out.pop("claims_json", None)
    if cj:
        try:
            out["claims"] = json.loads(cj)
        except json.JSONDecodeError:
            out["claims"] = []
    else:
        out["claims"] = []
    return out


def _postprocess_claims(
    data: dict[str, Any], max_claims: int, max_quote_chars: int
) -> dict[str, Any]:
    claims = data.get("claims")
    if not isinstance(claims, list):
        data["claims"] = []
        return data
    claims = claims[:max_claims]
    seq = 0
    for c in claims:
        if not isinstance(c, dict):
            continue
        seq += 1
        c["claim_id"] = seq
        ev = c.get("evidence_lines")
        if not isinstance(ev, list):
            c["evidence_lines"] = []
            continue
        for e in ev:
            if not isinstance(e, dict):
                continue
            q = e.get("quote")
            if isinstance(q, str) and len(q) > max_quote_chars:
                e["quote"] = q[: max_quote_chars - 1] + "…"
                LOG.warning(
                    "Truncated quote to %s chars (claim_id=%s)",
                    max_quote_chars,
                    c.get("claim_id"),
                )
    data["claims"] = claims
    return data


def build_prompt(template: str, max_claims: int, max_quote_chars: int) -> str:
    return (
        template.replace("{{MAX_CLAIMS}}", str(max_claims)).replace(
            "{{MAX_QUOTE_CHARS}}", str(max_quote_chars)
        )
    )


def _genai_client(api_key: str) -> genai.Client:
    """
    google-genai gọi get_env_api_key() khi khởi tạo; nếu cả GOOGLE_API_KEY và GEMINI_API_KEY
    đều có, SDK in cảnh báo dù đã truyền api_key=. Tạm gỡ GOOGLE_API_KEY trong lúc tạo Client
    để tránh cảnh báo (key thực tế vẫn là tham số api_key).
    """
    google_backup = os.environ.pop("GOOGLE_API_KEY", None)
    try:
        return genai.Client(api_key=api_key)
    finally:
        if google_backup is not None:
            os.environ["GOOGLE_API_KEY"] = google_backup


def process_pdf(
    client: genai.Client,
    pdf_path: Path,
    prompt_text: str,
    metadata: dict,
    model_name: str,
    temperature: float,
    max_claims: int,
    max_quote_chars: int,
    *,
    low_text_chars_per_page: int = DEFAULT_LOW_TEXT_CHARS_PER_PAGE,
    metadata_in_lookup: bool = True,
) -> dict[str, Any]:
    """Process one PDF; return flat row for CSV including claims_json."""
    file_size = pdf_path.stat().st_size
    row: dict[str, Any] = {
        "pdf_filename": pdf_path.name,
        "company_name": metadata.get("company_name", ""),
        "company_ticker": metadata.get("company_ticker", ""),
        "company_sector": metadata.get("company_sector", ""),
        "report_year": metadata.get("report_year", ""),
        "report_type": metadata.get("report_type", ""),
        "report_lang": metadata.get("report_lang", ""),
        "report_pages": metadata.get("report_pages", ""),
        "model_used": model_name,
        "extraction_status": "ok",
        "parse_error": "",
        "metadata_in_lookup": "true" if metadata_in_lookup else "false",
        "text_extraction_mode": "",
        "local_truncated": "",
        "local_low_text_density": "",
        "chars_per_page_avg": "",
        "api_finish_reason": "",
        "prompt_block_reason": "",
    }
    for k in FLAT_KEYS:
        row[k] = ""

    gemini_file = None
    try:
        if file_size <= MAX_UPLOAD_SIZE:
            LOG.info(
                "Uploading file: %s (%.1f MB) model=%s",
                pdf_path.name,
                file_size / 1024 / 1024,
                model_name,
            )
            gemini_file = client.files.upload(
                file=str(pdf_path), config={"display_name": pdf_path.name}
            )
            state = gemini_file.state
            while state.name == "PROCESSING":
                time.sleep(2)
                gemini_file = client.files.get(name=gemini_file.name)
                state = gemini_file.state
            if state.name == "FAILED":
                raise ValueError("File processing failed on Gemini side")
            content: list[Any] = [gemini_file, prompt_text]
            row["text_extraction_mode"] = "upload"
        else:
            LOG.info(
                "File > upload limit. Local text extraction: %s (%.1f MB)",
                pdf_path.name,
                file_size / 1024 / 1024,
            )
            text, loc_diag = extract_text_locally(
                pdf_path, min_chars_per_page=low_text_chars_per_page
            )
            row["text_extraction_mode"] = "local"
            row["local_truncated"] = "true" if loc_diag.get("truncated") else "false"
            row["local_low_text_density"] = (
                "true" if loc_diag.get("low_text_density") else "false"
            )
            row["chars_per_page_avg"] = str(loc_diag.get("chars_per_page_avg", ""))
            if not text.strip():
                raise ValueError("Extracted text was empty")
            content = [
                f"Here is the text extracted from the report:\n\n{text}\n\n{prompt_text}"
            ]

        LOG.info("Calling Gemini model=%s temperature=%s", model_name, temperature)
        response = client.models.generate_content(
            model=model_name,
            contents=content,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=temperature,
            ),
        )
        raw_text = getattr(response, "text", None) or ""
        if not raw_text.strip():
            dbg = _response_debug(response)
            row["api_finish_reason"] = str(dbg.get("finish_reason", "") or "")
            row["prompt_block_reason"] = str(dbg.get("prompt_block_reason", "") or "")
            LOG.error(
                "Empty model response | pdf=%s | debug=%s",
                pdf_path.name,
                dbg,
            )
            row["extraction_status"] = "error"
            row["parse_error"] = "empty_model_response"
            return row

        parsed, err = parse_json_response(raw_text)
        if err:
            row["extraction_status"] = "parse_error"
            row["parse_error"] = err
            row["claims_json"] = ""
            return row

        parsed = _postprocess_claims(parsed, max_claims, max_quote_chars)

        for k in FLAT_KEYS:
            if k in parsed:
                val = parsed[k]
                if k == "has_net_zero_commitment":
                    row[k] = _bool_to_csv(val)
                else:
                    row[k] = "" if val is None else str(val)

        claims = parsed.get("claims")
        row["claims_json"] = (
            json.dumps(claims, ensure_ascii=False) if isinstance(claims, list) else "[]"
        )

        if not isinstance(parsed.get("claims"), list):
            row["extraction_status"] = "partial"
            row["parse_error"] = "missing_or_invalid_claims_array"
        elif len(parsed.get("claims", [])) == 0:
            row["extraction_status"] = "partial"
            row["parse_error"] = "empty_claims"

    except Exception as e:
        row["extraction_status"] = "error"
        row["parse_error"] = str(e)
        row["claims_json"] = ""
        LOG.error("Processing failed for %s: %s", pdf_path.name, e, exc_info=True)
    finally:
        if gemini_file:
            try:
                client.files.delete(name=gemini_file.name)
            except Exception as e:
                LOG.warning("Failed to delete uploaded file %s: %s", gemini_file.name, e)

    return row


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    _ensure_repo_on_path()
    from config.settings import (
        ENV_FILE_CONFIG,
        ENV_FILE_ROOT,
        get_bool,
        get_float,
        get_int,
        get_int_optional,
        get_path,
        get_path_optional,
        get_str,
        load_env,
    )

    load_env()

    parser = argparse.ArgumentParser(
        description="Extract ESG + vagueness + claim-evidence JSON from sustainability PDFs.",
        epilog="Giá trị mặc định lấy từ config/.env (xem config/.env.example).",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=get_path("GEMINI_PDF_DIR", "data/vietnam_sustainabilityreports/pdfs"),
    )
    parser.add_argument(
        "--reports-json",
        type=Path,
        default=get_path(
            "GEMINI_REPORTS_JSON",
            "data/vietnam_sustainabilityreports/vietnam_reports.json",
        ),
    )
    parser.add_argument(
        "--companies-json",
        type=Path,
        default=get_path(
            "GEMINI_COMPANIES_JSON",
            "data/vietnam_sustainabilityreports/vietnam_companies.json",
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=get_path("GEMINI_OUTPUT_CSV", "data/esg_extracted.csv"),
    )
    parser.add_argument(
        "--skip-existing",
        action=argparse.BooleanOptionalAction,
        default=get_bool("GEMINI_SKIP_EXISTING", False),
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=get_float("GEMINI_DELAY_SECONDS", 2.0),
    )
    parser.add_argument("--max-files", type=int, default=get_int_optional("GEMINI_MAX_FILES"))
    parser.add_argument(
        "--log-file",
        type=Path,
        default=get_path("GEMINI_LOG_FILE", "logs/extraction.log"),
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        default=get_path("GEMINI_PROMPT_FILE", "config/esg_extraction_prompt.txt"),
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=get_float("GEMINI_TEMPERATURE", 0.0),
        help="Sampling temperature (default từ GEMINI_TEMPERATURE hoặc 0.0)",
    )
    parser.add_argument(
        "--max-claims",
        type=int,
        default=get_int("GEMINI_MAX_CLAIMS", 10),
        help="Max claims per report",
    )
    parser.add_argument(
        "--max-quote-chars",
        type=int,
        default=get_int("GEMINI_MAX_QUOTE_CHARS", 500),
    )
    parser.add_argument(
        "--model-pro",
        default=get_str("GEMINI_MODEL_PRO", "gemini-2.5-pro"),
        help="Model cho N file đầu (hoặc GEMINI_MODEL_PRO trong .env)",
    )
    parser.add_argument(
        "--model-batch",
        default=get_str("GEMINI_MODEL_BATCH", "gemini-2.5-flash"),
        help="Model cho batch (hoặc GEMINI_MODEL_BATCH)",
    )
    parser.add_argument(
        "--sample-pro-n",
        type=int,
        default=get_int("GEMINI_SAMPLE_PRO_N", 5),
    )
    parser.add_argument(
        "--low-text-chars-per-page",
        type=int,
        default=get_int(
            "GEMINI_LOW_TEXT_CHARS_PER_PAGE", DEFAULT_LOW_TEXT_CHARS_PER_PAGE
        ),
        help="Cảnh báo PDF scan/thiếu chữ: trung bình ký tự/trang < ngưỡng (PyMuPDF).",
    )
    parser.add_argument(
        "--jsonl-output",
        type=Path,
        default=None,
        help="Đường dẫn file JSONL (một dòng/báo cáo). Mặc định: GEMINI_JSONL_OUTPUT hoặc cùng base với --output .jsonl.",
    )
    parser.add_argument(
        "--no-jsonl",
        action="store_true",
        help="Không ghi JSONL (ghi mặc định nếu GEMINI_WRITE_JSONL=true trong .env).",
    )
    args = parser.parse_args()

    _repo_root = Path(__file__).resolve().parent.parent

    def _abs(p: Path) -> Path:
        return p if p.is_absolute() else (_repo_root / p).resolve()

    args.output = _abs(args.output)
    args.pdf_dir = _abs(args.pdf_dir)
    args.reports_json = _abs(args.reports_json)
    args.companies_json = _abs(args.companies_json)
    args.log_file = _abs(args.log_file)
    args.prompt_file = _abs(args.prompt_file)
    if args.jsonl_output is not None:
        args.jsonl_output = _abs(args.jsonl_output)

    _configure_logging(args.log_file)
    if ENV_FILE_CONFIG.is_file():
        LOG.info("Biến môi trường: %s", ENV_FILE_CONFIG)
    elif ENV_FILE_ROOT.is_file():
        LOG.info("Biến môi trường: %s", ENV_FILE_ROOT)
    else:
        LOG.warning(
            "Không tìm thấy %s hoặc %s — chỉ dùng biến hệ thống",
            ENV_FILE_CONFIG,
            ENV_FILE_ROOT,
        )

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        LOG.error(
            "Chưa có API key: đặt GEMINI_API_KEY (ưu tiên) hoặc GOOGLE_API_KEY trong %s.",
            ENV_FILE_CONFIG,
        )
        sys.exit(1)
    if not args.prompt_file.exists():
        LOG.error("Prompt file not found: %s", args.prompt_file)
        sys.exit(1)

    template = args.prompt_file.read_text(encoding="utf-8")
    prompt_text = build_prompt(template, args.max_claims, args.max_quote_chars)

    client = _genai_client(api_key)
    metadata_lookup = load_metadata(args.reports_json, args.companies_json)
    pdfs = sorted(args.pdf_dir.glob("*.pdf"), key=lambda p: p.name)
    if args.max_files is not None:
        pdfs = pdfs[: args.max_files]

    write_jsonl = get_bool("GEMINI_WRITE_JSONL", True) and not args.no_jsonl
    jsonl_path: Path | None = None
    if write_jsonl:
        if args.jsonl_output is not None:
            jsonl_path = args.jsonl_output
        else:
            env_j = get_path_optional("GEMINI_JSONL_OUTPUT")
            jsonl_path = env_j if env_j is not None else args.output.with_suffix(".jsonl")

    LOG.info(
        "PDFs=%s | max_claims=%s max_quote=%s | pro=%s (first %s) batch=%s | temp=%s",
        len(pdfs),
        args.max_claims,
        args.max_quote_chars,
        args.model_pro,
        args.sample_pro_n,
        args.model_batch,
        args.temperature,
    )
    if jsonl_path:
        LOG.info("JSONL: %s", jsonl_path)

    existing_files: set[str] = set()
    if args.skip_existing and args.output.exists():
        try:
            with open(args.output, encoding="utf-8") as f:
                existing_files = {
                    r.get("pdf_filename", "")
                    for r in csv.DictReader(f)
                    if r.get("pdf_filename")
                }
            LOG.info("skip-existing: %s rows already in CSV", len(existing_files))
        except Exception as e:
            LOG.warning("Could not read existing CSV: %s", e)

    fieldnames = [
        "pdf_filename",
        "company_name",
        "company_ticker",
        "company_sector",
        "report_year",
        "report_type",
        "report_lang",
        "report_pages",
        "model_used",
        "extraction_status",
        "parse_error",
        "metadata_in_lookup",
        "text_extraction_mode",
        "local_truncated",
        "local_low_text_density",
        "chars_per_page_avg",
        "api_finish_reason",
        "prompt_block_reason",
        *FLAT_KEYS,
        "claims_json",
    ]

    write_header = not args.output.exists() or not args.skip_existing
    processed_idx = 0
    to_run = [p for p in pdfs if p.name not in existing_files]

    with open(
        args.output, "a" if args.skip_existing else "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()

        for pdf_path in to_run:
            model_name = (
                args.model_pro
                if processed_idx < args.sample_pro_n
                else args.model_batch
            )
            LOG.info(
                "[%s/%s] %s | model=%s",
                processed_idx + 1,
                len(to_run),
                pdf_path.name,
                model_name,
            )
            meta = metadata_lookup.get(pdf_path.name, {})
            if pdf_path.name not in metadata_lookup:
                LOG.warning(
                    "PDF không có trong metadata lookup (reports JSON): %s",
                    pdf_path.name,
                )
            in_lookup = pdf_path.name in metadata_lookup
            retries = 3
            row: Optional[dict[str, Any]] = None
            for attempt in range(retries):
                try:
                    row = process_pdf(
                        client,
                        pdf_path,
                        prompt_text,
                        meta,
                        model_name=model_name,
                        temperature=args.temperature,
                        max_claims=args.max_claims,
                        max_quote_chars=args.max_quote_chars,
                        low_text_chars_per_page=args.low_text_chars_per_page,
                        metadata_in_lookup=in_lookup,
                    )
                    st = row.get("extraction_status")
                    if st == "parse_error":
                        break
                    if st in ("ok", "partial"):
                        break
                    if st == "error" and attempt < retries - 1:
                        LOG.warning(
                            "Retry %s/%s sau lỗi (không retry parse_error): status=%s parse_error=%s",
                            attempt + 1,
                            retries,
                            st,
                            row.get("parse_error"),
                        )
                        time.sleep(5)
                        continue
                    break
                except Exception as e:
                    LOG.warning("Attempt %s exception: %s", attempt + 1, e)
                    if attempt < retries - 1:
                        time.sleep(5)
            if row:
                writer.writerow(row)
                f.flush()
                if jsonl_path:
                    _append_jsonl(jsonl_path, row_to_jsonl_record(row))
            processed_idx += 1
            time.sleep(args.delay)

    LOG.info("Processing complete.")


if __name__ == "__main__":
    main()
