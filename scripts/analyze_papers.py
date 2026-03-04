#!/usr/bin/env python3
"""
Paper Analyzer v5
- PDF 전체를 Claude API에 직접 전달 (1-stage, 안정적)
- Default: pro (Opus 4.6), fallback chain
- arXiv + Semantic Scholar API로 메타데이터 보강 (institution 포함)
- MkDocs Material 출력
"""

import os, sys, re, json, time, base64, argparse
import urllib.request, urllib.parse, xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import anthropic

# --- Config ---
RESULTS_DIR = Path("docs") / "papers"
INPUTS_DIR = Path("inputs")
PDFS_DIR = INPUTS_DIR / "pdfs"
FIGURES_DIR = RESULTS_DIR / "figures"
STATE_FILE = Path("results") / ".state.json"

MODELS = {
    "free": [
        "claude-sonnet-4-5-20250929",
        "claude-haiku-4-5-20251001",
    ],
    "pro": [
        "claude-opus-4-6",
        "claude-sonnet-4-5-20250929",
        "claude-haiku-4-5-20251001",
    ],
}
MAX_TOKENS = 8192
HTTP_TIMEOUT = 30

# --- Data ---
@dataclass
class ExtractedFigure:
    image_path: str
    page_num: int
    caption: str = ""

# === State ===
def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def title_to_slug(title):
    s = re.sub(r"[^\w\s-]", "", title.lower())
    return re.sub(r"[\s_]+", "_", s).strip("_")[:120]


# =====================================================
# Input: paper_links.txt
# =====================================================

def parse_paper_links(filepath):
    papers = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            papers.append({
                "url": line,
                "title": "", "author": "", "year": "",
                "doi": "", "journal": "", "abstract": "",
                "institution": "", "pdf_path": "", "arxiv_id": "",
            })
    return papers


# =====================================================
# arXiv API (무료 메타데이터)
# =====================================================

def _extract_arxiv_id(text):
    if not text:
        return None
    for pat in [r"(\d{4}\.\d{4,5}(?:v\d+)?)", r"([\w\-]+/\d{7})"]:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return None


def fetch_arxiv_meta(arxiv_id):
    if not arxiv_id:
        return None
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    print(f"    arXiv API: {arxiv_id}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "paper-analyzer/1.0"})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            xml_data = r.read().decode("utf-8")
        ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
        entry = ET.fromstring(xml_data).find("a:entry", ns)
        if entry is None:
            return None
        title = entry.findtext("a:title", "", ns).replace("\n", " ").strip()
        abstract = entry.findtext("a:summary", "", ns).replace("\n", " ").strip()
        authors = [a.findtext("a:name", "", ns) for a in entry.findall("a:author", ns)]
        pub = entry.findtext("a:published", "", ns)[:10]
        jref = entry.findtext("x:journal_ref", "", ns)
        pcat = entry.find("x:primary_category", ns)
        cat = pcat.get("term", "") if pcat is not None else ""
        affs = [a.findtext("x:affiliation", "", ns) for a in entry.findall("a:author", ns)]
        return {
            "title": title,
            "abstract": abstract,
            "author": ", ".join(authors),
            "year": pub[:4] if pub else "",
            "journal": jref or f"arXiv:{arxiv_id} [{cat}]",
            "institution": ", ".join(set(a for a in affs if a)),
            "url": f"https://arxiv.org/abs/{arxiv_id}",
        }
    except Exception as e:
        print(f"    [WARN] arXiv API: {e}")
        return None


# =====================================================
# Semantic Scholar API (institution 보강)
# =====================================================

def fetch_s2_meta(title):
    """Semantic Scholar API로 institution 등 메타데이터 보강."""
    if not title:
        return None
    query = urllib.parse.quote(title[:200])
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=1&fields=title,authors,venue,year,externalIds"
    print(f"    S2 API: {title[:50]}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "paper-analyzer/1.0"})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8"))
        papers = data.get("data", [])
        if not papers:
            return None
        p = papers[0]

        # Author affiliations
        affiliations = []
        authors_with_aff = p.get("authors", [])
        for a in authors_with_aff:
            affs = a.get("affiliations", [])
            if affs:
                affiliations.extend(affs)

        # If no affiliations in search, try paper detail
        if not affiliations:
            pid = p.get("paperId", "")
            if pid:
                detail_url = f"https://api.semanticscholar.org/graph/v1/paper/{pid}?fields=authors.affiliations"
                try:
                    req2 = urllib.request.Request(detail_url, headers={"User-Agent": "paper-analyzer/1.0"})
                    with urllib.request.urlopen(req2, timeout=HTTP_TIMEOUT) as r2:
                        detail = json.loads(r2.read().decode("utf-8"))
                    for a in detail.get("authors", []):
                        affs = a.get("affiliations", [])
                        if affs:
                            affiliations.extend(affs)
                except Exception:
                    pass

        result = {
            "institution": ", ".join(sorted(set(a for a in affiliations if a))),
        }

        # Also grab venue/year if available
        if p.get("venue"):
            result["journal"] = p["venue"]
        if p.get("year"):
            result["year"] = str(p["year"])

        # ArXiv ID from externalIds
        ext_ids = p.get("externalIds", {})
        if ext_ids.get("ArXiv"):
            result["arxiv_id"] = ext_ids["ArXiv"]

        return result
    except Exception as e:
        print(f"    [WARN] S2 API: {e}")
        return None


def enrich_metadata(paper):
    """arXiv + Semantic Scholar API로 메타데이터 보강."""
    # 1. arXiv ID 확보
    aid = paper.get("arxiv_id", "")
    if not aid:
        aid = _extract_arxiv_id(paper.get("url", ""))
        if aid:
            paper["arxiv_id"] = aid

    # 2. arXiv API
    if aid:
        meta = fetch_arxiv_meta(aid)
        if meta:
            for k in ("title", "abstract", "author", "year", "journal", "institution", "url"):
                if not paper.get(k) and meta.get(k):
                    paper[k] = meta[k]
            print(f"    ✓ arXiv metadata enriched")

    # 3. Semantic Scholar (institution 보강)
    title = paper.get("title", "")
    if title and not paper.get("institution"):
        s2 = fetch_s2_meta(title)
        if s2:
            for k, v in s2.items():
                if v and not paper.get(k):
                    paper[k] = v
            if s2.get("institution"):
                print(f"    ✓ S2 institution: {s2['institution'][:60]}")


# =====================================================
# PDF Acquisition (2-step: local or download)
# =====================================================

def _download_pdf(url, dest):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "paper-analyzer/1.0"})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            data = r.read()
            if data[:5] != b"%PDF-":
                print(f"    [WARN] Not a PDF: {url}")
                return False
            with open(dest, "wb") as f:
                f.write(data)
            return True
    except Exception as e:
        print(f"    [WARN] Download failed: {e}")
        return False


def acquire_pdf(paper):
    title = paper.get("title", "")
    if title:
        slug = title_to_slug(title)
    else:
        aid = paper.get("arxiv_id", "") or _extract_arxiv_id(paper.get("url", ""))
        slug = aid.replace(".", "_").replace("/", "_") if aid else "unknown"
    PDFS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  PDF:")

    # Step 1: local
    lp = paper.get("pdf_path", "")
    if lp and os.path.isfile(lp):
        print(f"    ✓ Local: {lp}")
        return lp
    cand = PDFS_DIR / f"{slug}.pdf"
    if cand.exists():
        print(f"    ✓ Local: {cand}")
        return str(cand)
    for f in PDFS_DIR.glob("*.pdf"):
        if slug[:30] in f.stem.lower():
            print(f"    ✓ Local match: {f}")
            return str(f)

    # Step 2: download
    dest = str(PDFS_DIR / f"{slug}.pdf")
    aid = paper.get("arxiv_id", "") or _extract_arxiv_id(paper.get("url", ""))
    if aid:
        arxiv_url = f"https://arxiv.org/pdf/{aid}.pdf"
        print(f"    arXiv PDF: {arxiv_url}")
        if _download_pdf(arxiv_url, dest):
            paper["pdf_path"] = dest
            return dest
    url = paper.get("url", "")
    if url and url.lower().endswith(".pdf"):
        print(f"    Direct PDF: {url}")
        if _download_pdf(url, dest):
            paper["pdf_path"] = dest
            return dest

    print(f"    FAIL")
    return None


# =====================================================
# Figure Extraction
# =====================================================

def _page_captions(text):
    return [
        m.group(1).strip().replace("\n", " ")
        for m in re.finditer(
            r"((?:Figure|Fig\.?|Table)\s*\d+[\s.:]+.+?)(?:\n\n|\n(?=[A-Z\d])|$)",
            text, re.I | re.DOTALL)
        if len(m.group(1).strip()) > 15
    ]


def extract_figures(pdf_path, slug):
    if not pdf_path or not os.path.isfile(pdf_path):
        return []
    fd = FIGURES_DIR / slug
    fd.mkdir(parents=True, exist_ok=True)
    results = []
    try:
        import fitz
        doc = fitz.open(pdf_path)
        ii = 0
        for pn in range(len(doc)):
            pg = doc[pn]
            imgs = pg.get_images(full=True)
            caps = _page_captions(pg.get_text("text"))
            pf = []
            for img in imgs:
                b = doc.extract_image(img[0])
                if b and len(b["image"]) >= 5000:
                    fn = f"fig_p{pn+1}_{ii}.{b.get('ext', 'png')}"
                    fp = fd / fn
                    with open(fp, "wb") as f:
                        f.write(b["image"])
                    pf.append(ExtractedFigure(str(fp), pn + 1))
                    ii += 1
            for i, fig in enumerate(pf):
                if i < len(caps):
                    fig.caption = caps[i]
                results.append(fig)
        doc.close()
    except ImportError:
        print("  [WARN] PyMuPDF not installed")
    except Exception as e:
        print(f"  [WARN] Figure extraction: {e}")
    return results


# =====================================================
# Claude API
# =====================================================

def call_claude(client, msgs, sys_prompt, chain, max_tok=MAX_TOKENS):
    """Returns (response_text, model_used)."""
    for model in chain:
        try:
            print(f"    -> {model}")
            r = client.messages.create(
                model=model, max_tokens=max_tok,
                system=sys_prompt, messages=msgs,
            )
            u = r.usage
            print(f"    OK  in:{u.input_tokens:,} out:{u.output_tokens:,}")
            return r.content[0].text, model
        except anthropic.NotFoundError:
            print(f"    unavailable, next...")
        except anthropic.RateLimitError:
            print(f"    rate-limited, wait 60s...")
            time.sleep(60)
            try:
                r = client.messages.create(
                    model=model, max_tokens=max_tok,
                    system=sys_prompt, messages=msgs,
                )
                return r.content[0].text, model
            except Exception:
                continue
        except Exception as e:
            print(f"    error: {e}")
    return None, ""


# =====================================================
# Prompt (1-stage, PDF 전체)
# =====================================================

SYSTEM_PROMPT = """You are an expert academic paper analyzer.
You receive a full PDF of an academic paper. Analyze the entire paper and produce a structured summary.

RULES:
- Write in Korean. Keep technical terms in English (RAG, TTS, SOTA, fine-tuning, transformer, benchmark, etc.)
- Do NOT produce an Abstract section (it is inserted separately from arXiv metadata).
- If information is insufficient for a section, write "정보 부족".
- Be specific: include exact numbers, dataset names, model names, and comparison results.

OUTPUT FORMAT (follow exactly):

### 1. Abstract 요약
[Synthesize the paper's core contribution and findings into a Korean summary paragraph]

### 2. 한 줄 핵심 요약
[One-line core summary of the paper]

### 3. Contribution
[List the key contributions of this paper]

### 4. Methods
#### 핵심 아이디어
[Core idea / motivation]
#### 모델 구조
[Architecture details]
#### 데이터셋
[Datasets used]
#### 평가방법
[Evaluation metrics]
#### 실험 결과
[Key experimental results with numbers]

### 5. Findings
#### Objective Evaluations
[Quantitative results, benchmarks, comparisons]
#### Subjective Evaluations
[Qualitative analysis, case studies, human evaluation if any]

### 6. Notes
#### 의미
[Significance and impact]
#### 한계
[Limitations]
#### 코드/데모
[Code/demo links if mentioned in the paper]
"""


def build_message_with_pdf(paper, pdf_path):
    """PDF를 base64로 인코딩하여 Claude API 메시지 구성."""
    with open(pdf_path, "rb") as f:
        pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

    content = [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_data,
            },
        },
        {
            "type": "text",
            "text": (
                f"Analyze this paper.\n"
                f"Title: {paper.get('title', 'Unknown')}\n"
                f"Authors: {paper.get('author', 'Unknown')}\n"
                f"Year: {paper.get('year', '')}\n"
                f"Venue: {paper.get('journal', '')}\n"
            ),
        },
    ]
    return [{"role": "user", "content": content}]


# =====================================================
# Markdown Assembly
# =====================================================

def assemble_md(paper, abstract, summary, figures, model_used):
    title = paper.get("title", "Unknown")
    institution = paper.get("institution", "")
    md = [f"# {title}\n"]
    md.append(f"**Link**: {paper.get('url', 'N/A')}  ")
    md.append(f"**Authors**: {paper.get('author', 'Unknown')}  ")
    if institution:
        md.append(f"**Institution**: {institution}  ")
    md.append(f"**Venue**: {paper.get('journal', 'Unknown')} ({paper.get('year', '')})  ")
    md.append(f"**Model**: `{model_used}`\n")
    md.append("---\n## Abstract\n")
    md.append((abstract or "(N/A)") + "\n")
    md.append("\n---\n## Summary\n")
    md.append(summary + "\n")
    md.append("\n---\n### 7. Figures/Tables\n")
    if figures:
        for fig in figures:
            rel = os.path.relpath(fig.image_path, RESULTS_DIR)
            cap = fig.caption or f"(p.{fig.page_num})"
            md.append(f"**{cap}**\n\n![{cap}]({rel})\n")
    else:
        md.append("(none)\n")
    return "\n".join(md)


def assemble_missing_md(paper):
    title = paper.get("title", paper.get("url", "Unknown"))
    url = paper.get("url", "N/A")
    return (
        f"# {title}\n\n"
        f"!!! failure \"PDF not found\"\n"
        f"    Add PDF to `inputs/pdfs/` or check the URL, then re-run.\n\n"
        f"**Link**: {url}\n\n---\n(waiting for PDF)\n"
    )


# =====================================================
# Main Processing
# =====================================================

def process_paper(client, paper, state, tier="pro", force=False):
    # Enrich metadata first
    enrich_metadata(paper)

    title = paper.get("title", "")
    url = paper.get("url", "")
    if not title and not url:
        print("  [SKIP] No title or URL")
        return "failed"

    if title:
        slug = title_to_slug(title)
    else:
        aid = paper.get("arxiv_id", "") or _extract_arxiv_id(url)
        slug = aid.replace(".", "_").replace("/", "_") if aid else title_to_slug(url[-40:])

    out = RESULTS_DIR / f"{slug}.md"
    ps = state.get(slug, {})

    if not force:
        if ps.get("status") == "done" and out.exists():
            print(f"  [SKIP] Done: {slug}")
            return "skipped"
        if ps.get("status") == "missing_pdf":
            cand = PDFS_DIR / f"{slug}.pdf"
            has_local = cand.exists() or any(
                slug[:30] in f.stem.lower() for f in PDFS_DIR.glob("*.pdf")
            )
            if not has_local:
                print(f"  [SKIP] Still missing_pdf: {slug}")
                return "skipped"

    display = title or url
    print(f"\n{'=' * 60}")
    print(f"  {display[:80]}")
    print(f"{'=' * 60}")

    # --- PDF ---
    pdf = acquire_pdf(paper)
    if not pdf:
        state[slug] = {"status": "missing_pdf", "title": title or url}
        save_state(state)
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            f.write(assemble_missing_md(paper))
        return "missing_pdf"

    # --- Figures ---
    figs = extract_figures(pdf, slug)
    if figs:
        print(f"  Figures: {len(figs)}")

    # --- Abstract (from arXiv, not Claude) ---
    abstract = paper.get("abstract", "")

    # --- Claude: PDF 전체 1-stage ---
    chain = MODELS.get(tier, MODELS["pro"])

    print(f"\n  Analyzing ({tier})...")
    msgs = build_message_with_pdf(paper, pdf)
    summary, model_used = call_claude(client, msgs, SYSTEM_PROMPT, chain, MAX_TOKENS)

    if not summary and tier == "pro":
        print(f"  Pro failed, falling back to free...")
        chain = MODELS["free"]
        summary, model_used = call_claude(client, msgs, SYSTEM_PROMPT, chain, MAX_TOKENS)

    if not summary:
        state[slug] = {"status": "failed", "title": title}
        save_state(state)
        return "failed"

    # --- Save ---
    md = assemble_md(paper, abstract, summary, figs, model_used)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        f.write(md)

    state[slug] = {
        "status": "done",
        "title": title,
        "model": model_used,
    }
    save_state(state)
    print(f"\n  Saved: {out}")
    return "processed"


# =====================================================
# CLI
# =====================================================

def main():
    ap = argparse.ArgumentParser(description="Paper Analyzer v5")
    ap.add_argument("--input", "-i", default="inputs/paper_links.txt")
    ap.add_argument("--force", "-f", action="store_true")
    ap.add_argument("--tier", "-t", choices=["free", "pro"], default="pro",
                    help="Model tier: pro=Opus (default), free=Sonnet")
    ap.add_argument("--paper", "-p", default=None)
    args = ap.parse_args()

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ERROR: Set ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=key)

    inp = args.input
    if not os.path.isfile(inp):
        for ext in ("*.txt",):
            found = list(INPUTS_DIR.glob(ext))
            if found:
                inp = str(found[0])
                break
        else:
            print(f"ERROR: {inp} not found")
            sys.exit(1)

    papers = parse_paper_links(inp)
    if not papers:
        print("No papers found.")
        sys.exit(0)

    state = load_state()
    print(f"Papers: {len(papers)} | Tier: {args.tier}")
    print(f"Models: {' -> '.join(MODELS[args.tier])}\n")

    if args.paper:
        papers = [
            p for p in papers
            if args.paper.lower() in (p.get("title", "") + p.get("url", "")).lower()
        ]

    ct = {"processed": 0, "skipped": 0, "missing_pdf": 0, "failed": 0}
    for paper in papers:
        r = process_paper(client, paper, state, tier=args.tier, force=args.force)
        ct[r] += 1
        if ct["processed"] > 0 and ct["processed"] % 5 == 0:
            print("\n  [Rate limit pause 10s...]")
            time.sleep(10)

    save_state(state)

    print(f"\n{'=' * 60}")
    print(f"  Processed:   {ct['processed']}")
    print(f"  Skipped:     {ct['skipped']}")
    print(f"  Missing PDF: {ct['missing_pdf']}")
    print(f"  Failed:      {ct['failed']}")
    print(f"{'=' * 60}")

    miss = [v["title"] for v in state.values() if v.get("status") == "missing_pdf"]
    if miss:
        print(f"\n  PDF missing ({len(miss)}):")
        for t in miss:
            print(f"   - {t}")


if __name__ == "__main__":
    main()
