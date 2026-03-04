#!/usr/bin/env python3
"""Paper Analyzer v4 - Sonnet default, paper_links.txt input, MkDocs output"""

import os, sys, re, json, time, argparse
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
MAX_TOK1 = 8192
MAX_TOK2 = 4096
HTTP_TIMEOUT = 30

# --- Data ---
@dataclass
class PaperSections:
    abstract: str = ""
    introduction: str = ""
    method: str = ""
    experiments: str = ""
    conclusion: str = ""
    raw_full_text: str = ""

@dataclass
class ExtractedFigure:
    image_path: str
    page_num: int
    caption: str = ""

# --- State ---
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
    """
    paper_links.txt 파싱.
    한 줄에 URL 하나. '#'으로 시작하면 주석.
    지원: arXiv URL, 직접 PDF URL
    """
    papers = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            papers.append({
                "url": line,
                "title": "",
                "author": "",
                "year": "",
                "doi": "",
                "journal": "",
                "abstract": "",
                "institution": "",
                "pdf_path": "",
                "arxiv_id": "",
            })
    return papers


# =====================================================
# arXiv API (무료 메타데이터, Claude 토큰 절감)
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


def enrich_metadata(paper):
    """arXiv API로 메타데이터 보강 (빈 필드만 채움)."""
    aid = paper.get("arxiv_id", "")
    if not aid:
        aid = _extract_arxiv_id(paper.get("url", ""))
        if aid:
            paper["arxiv_id"] = aid
    if not aid:
        return
    meta = fetch_arxiv_meta(aid)
    if not meta:
        return
    for k in ("title", "abstract", "author", "year", "journal", "institution", "url"):
        if not paper.get(k) and meta.get(k):
            paper[k] = meta[k]
    print(f"    ✓ Metadata enriched via arXiv")


# =====================================================
# PDF Acquisition (2-step)
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
    """PDF 취득: (1) 로컬 (2) URL 다운로드 (arXiv or direct PDF)."""
    title = paper.get("title", "")
    if not title:
        # title 없으면 slug를 URL 기반으로
        aid = paper.get("arxiv_id", "") or _extract_arxiv_id(paper.get("url", ""))
        slug = aid.replace(".", "_").replace("/", "_") if aid else "unknown"
    else:
        slug = title_to_slug(title)
    PDFS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  PDF:")

    # Step 1: 로컬
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

    # Step 2: 다운로드
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
# PDF Section Extraction
# =====================================================

_SEC_PAT = {
    "abstract": [r"^abstract\b"],
    "introduction": [r"^\d*\.?\s*introduction\b"],
    "related_work": [r"^\d*\.?\s*related\s+work\b", r"^\d*\.?\s*background\b"],
    "method": [
        r"^\d*\.?\s*method(?:s|ology)?\b",
        r"^\d*\.?\s*(?:proposed\s+)?(?:approach|model|framework)\b",
        r"^\d*\.?\s*architecture\b",
        r"^\d*\.?\s*(?:the\s+)?(?:transformer|model\s+architecture)\b",
        r"^\d*\.?\s*(?:our\s+)?(?:approach|system|method)\b",
        r"^\d*\.?\s*(?:technical\s+)?approach\b",
        r"^\d*\.?\s*formulation\b",
        r"^\d*\.?\s*(?:problem\s+)?(?:setup|formulation|definition)\b",
        r"^\d*\.?\s*training\b",
    ],
    "experiments": [
        r"^\d*\.?\s*experiment(?:s|al)?\b",
        r"^\d*\.?\s*results?\b",
        r"^\d*\.?\s*evaluation\b",
        r"^\d*\.?\s*(?:results?\s+and\s+)?(?:analysis|discussion)\b",
        r"^\d*\.?\s*(?:empirical|ablation)\b",
        r"^\d*\.?\s*(?:why\s+)?self[- ]attention\b",
    ],
    "conclusion": [
        r"^\d*\.?\s*conclusion(?:s)?\b",
        r"^\d*\.?\s*(?:conclusion(?:s)?\s+and\s+)?future\s+work\b",
        r"^\d*\.?\s*concluding\s+remarks?\b",
        r"^\d*\.?\s*summary\b",
    ],
}


def _classify(heading):
    h = heading.lower().strip()
    for k, pats in _SEC_PAT.items():
        for p in pats:
            if re.search(p, h):
                return k
    return "other"


def extract_sections(pdf_path):
    if not pdf_path or not os.path.isfile(pdf_path):
        return None
    try:
        import fitz
    except ImportError:
        print("  [WARN] PyMuPDF not installed")
        return None
    try:
        doc = fitz.open(pdf_path)
        ft = "".join(p.get_text("text") + "\n" for p in doc)
        doc.close()
    except Exception as e:
        print(f"  [WARN] PDF read: {e}")
        return None
    if not ft.strip():
        return None

    sec = PaperSections(raw_full_text=ft)
    lines = ft.split("\n")
    segs = []
    for i, l in enumerate(lines):
        s = l.strip()
        if not s or len(s) > 120:
            continue
        # Heading detection: multiple formats
        is_heading = False
        # "3 Model Architecture", "3. Model Architecture"
        if re.match(r"^\d+\.?\s+[A-Z]", s):
            is_heading = True
        # "III. Results", "IV Model"
        elif re.match(r"^[IVXLC]+\.?\s+[A-Z]", s):
            is_heading = True
        # "ALL CAPS HEADING" (max 8 words)
        elif s.isupper() and 1 <= len(s.split()) <= 8:
            is_heading = True
        # "Abstract", "Introduction", "Conclusion" standalone
        elif re.match(r"^(?:Abstract|Introduction|Conclusion|Discussion|References)\s*$", s, re.IGNORECASE):
            is_heading = True
        # "3.1 Encoder and Decoder Stacks" (subsection)
        elif re.match(r"^\d+\.\d+\.?\s+[A-Z]", s):
            # subsections -> classify parent section
            is_heading = True

        if is_heading:
            segs.append((_classify(s), i))

    for idx, (k, st) in enumerate(segs):
        end = segs[idx + 1][1] if idx + 1 < len(segs) else len(lines)
        blk = "\n".join(lines[st:end]).strip()
        if k == "abstract":
            sec.abstract = blk
        elif k == "introduction":
            sec.introduction = blk
        elif k == "method":
            sec.method = blk
        elif k == "experiments":
            sec.experiments = blk
        elif k == "conclusion":
            sec.conclusion = blk

    # Fallback
    if not sec.abstract:
        m = re.search(
            r"(?:^|\n)\s*(?:Abstract|ABSTRACT)\s*\n(.*?)(?=\n\s*\d*\.?\s*(?:Introduction|INTRODUCTION|1\s))",
            ft, re.DOTALL)
        if m:
            sec.abstract = m.group(1).strip()
    if not sec.conclusion:
        m = re.search(
            r"(?:^|\n)\s*\d*\.?\s*(?:Conclusion|CONCLUSION)\b.*?\n(.*?)(?=\n\s*(?:References|REFERENCES|\[1\]))",
            ft, re.DOTALL)
        if m:
            sec.conclusion = m.group(1).strip()

    return sec


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
# Helpers
# =====================================================

def _trunc(text, max_tok=6000):
    mc = max_tok * 4
    if len(text) <= mc:
        return text
    f = int(mc * 0.6)
    b = int(mc * 0.4)
    return text[:f] + "\n\n[... truncated ...]\n\n" + text[-b:]


# =====================================================
# Claude API
# =====================================================

def call_claude(client, msgs, sys_prompt, chain, max_tok=MAX_TOK1):
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
# Prompts
# =====================================================

SYS_STAGE1 = """You are an expert academic paper analyzer.
You receive extracted sections from a paper. Produce a structured summary.

RULES:
- Write in Korean. Keep technical terms in English (RAG, TTS, SOTA, fine-tuning, transformer, benchmark, etc.)
- Do NOT produce an Abstract section (it is inserted separately from arXiv metadata).
- If information is insufficient, write "정보 부족".

OUTPUT FORMAT (follow exactly):

### 1. Abstract 요약
[Synthesize abstract + introduction + conclusion into Korean summary]

### 2. 한 줄 핵심 요약
[One-line core summary]

### 3. Contribution
[Key contributions]

### 4. Methods
#### 핵심 아이디어
#### 모델 구조
#### 데이터셋
#### 평가방법
#### 실험 결과

### 5. Findings
#### Objective Evaluations
#### Subjective Evaluations

### 6. Notes
#### 의미
#### 한계
#### 코드/데모
"""

SYS_STAGE2 = """You are refining a paper summary. You receive:
1) A draft summary
2) Detailed Experiments/Results text

ENHANCE: Fill in sections marked "정보 부족" and add specific numbers and comparisons.
Write in Korean. Keep technical terms in English. Keep exact same markdown structure.
Output the COMPLETE updated summary (all sections)."""


# =====================================================
# Stage builders
# =====================================================

def build_stage1_msg(paper, sec):
    parts = [
        f"## Metadata",
        f"- Title: {paper.get('title', '')}",
        f"- Authors: {paper.get('author', '')}",
        f"- Year: {paper.get('year', '')}",
        f"- Venue: {paper.get('journal', '')}",
        "",
    ]
    if sec:
        for name, text, limit in [
            ("Abstract", sec.abstract or paper.get("abstract", ""), 2000),
            ("Introduction", sec.introduction, 4000),
            ("Method", sec.method, 4000),
            ("Experiments", sec.experiments, 3000),
            ("Conclusion", sec.conclusion, 2000),
        ]:
            if text:
                parts.append(f"## {name}")
                parts.append(_trunc(text, limit))
                parts.append("")
    else:
        ab = paper.get("abstract", "")
        if ab:
            parts.append(f"## Abstract")
            parts.append(ab)
        parts.append("\n(metadata only)")
    return "\n".join(parts)


def build_stage2_msg(draft, sec):
    parts = [f"## Draft\n{draft}\n\n---\n## Experiments detail\n"]
    if sec.experiments:
        parts.append(_trunc(sec.experiments, 8000))
    if sec.method:
        parts.append(f"\n## Method detail\n{_trunc(sec.method, 6000)}")
    parts.append("\n\nPlease enhance the draft with specific numbers and details.")
    return "\n".join(parts)


# =====================================================
# Markdown Assembly
# =====================================================

def assemble_md(paper, abstract, summary, figures, stage1_only, model_used):
    title = paper.get("title", "Unknown")
    md = [f"# {title}\n"]
    if stage1_only:
        md.append("!!! warning \"Stage 1 only\"\n    Stage 2 refinement was not performed. Methods/Findings may be limited.\n")
    md.append(f"**Link**: {paper.get('url', 'N/A')}  ")
    md.append(f"**Authors**: {paper.get('author', 'Unknown')}  ")
    md.append(f"**Institution**: {paper.get('institution', 'Unknown')}  ")
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

def process_paper(client, paper, state, tier="free", force=False):
    # Enrich metadata first (needed for title/slug)
    enrich_metadata(paper)

    title = paper.get("title", "")
    url = paper.get("url", "")
    if not title and not url:
        print("  [SKIP] No title or URL")
        return "failed"

    # slug: title-based if available, else arxiv-id or url hash
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

    # --- Sections ---
    sec = extract_sections(pdf)
    if sec:
        found = []
        if sec.abstract: found.append("abstract")
        if sec.introduction: found.append("intro")
        if sec.method: found.append("method")
        if sec.experiments: found.append("experiments")
        if sec.conclusion: found.append("conclusion")
        print(f"  Sections: {len(found)}/5 [{', '.join(found)}]")
        if not found:
            print(f"  [WARN] No sections detected - Stage 2 will be skipped")
    else:
        print(f"  [WARN] Section extraction returned None")

    # --- Figures ---
    figs = extract_figures(pdf, slug)
    if figs:
        print(f"  Figures: {len(figs)}")

    # --- Abstract ---
    abstract = paper.get("abstract", "")
    if not abstract and sec and sec.abstract:
        abstract = sec.abstract

    # --- Claude ---
    chain = MODELS.get(tier, MODELS["free"])

    print(f"\n  Stage 1 ({tier})...")
    s1 = build_stage1_msg(paper, sec)
    draft, m1 = call_claude(
        client, [{"role": "user", "content": s1}],
        SYS_STAGE1, chain, MAX_TOK1,
    )
    if not draft and tier == "pro":
        print(f"  Pro failed, falling back to free...")
        chain = MODELS["free"]
        draft, m1 = call_claude(
            client, [{"role": "user", "content": s1}],
            SYS_STAGE1, chain, MAX_TOK1,
        )
    if not draft:
        state[slug] = {"status": "failed", "title": title}
        save_state(state)
        return "failed"

    final, model_used = draft, m1
    stage1_only = True

    if sec and (sec.experiments or sec.method):
        print(f"\n  Stage 2...")
        s2 = build_stage2_msg(draft, sec)
        ref, m2 = call_claude(
            client, [{"role": "user", "content": s2}],
            SYS_STAGE2, chain, MAX_TOK2,
        )
        if ref:
            final, model_used = ref, m2
            stage1_only = False
            print(f"    Done")
        else:
            print(f"    Stage 2 failed, using Stage 1")
    else:
        print(f"  [SKIP] Stage 2 - insufficient sections")

    # --- Save ---
    md = assemble_md(paper, abstract, final, figs, stage1_only, model_used)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        f.write(md)

    state[slug] = {
        "status": "done",
        "title": title,
        "model": model_used,
        "stage1_only": stage1_only,
    }
    save_state(state)
    print(f"\n  Saved: {out}")
    return "processed"


# =====================================================
# CLI
# =====================================================

def main():
    ap = argparse.ArgumentParser(description="Paper Analyzer v4")
    ap.add_argument("--input", "-i", default="inputs/paper_links.txt",
                    help="Input file (default: inputs/paper_links.txt)")
    ap.add_argument("--force", "-f", action="store_true",
                    help="Force re-analysis")
    ap.add_argument("--tier", "-t", choices=["free", "pro"], default="free",
                    help="Model tier: free=Sonnet (default), pro=Opus")
    ap.add_argument("--paper", "-p", default=None,
                    help="Process specific paper (title/URL substring match)")
    args = ap.parse_args()

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ERROR: Set ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=key)

    inp = args.input
    if not os.path.isfile(inp):
        # Auto-detect
        for ext in ("*.txt", "*.bib", "*.csv"):
            found = list(INPUTS_DIR.glob(ext))
            if found:
                inp = str(found[0])
                break
        else:
            print(f"ERROR: {inp} not found")
            sys.exit(1)

    # Parse based on extension
    ext = Path(inp).suffix.lower()
    if ext == ".txt":
        papers = parse_paper_links(inp)
    else:
        print(f"ERROR: Only .txt (paper_links.txt) supported. Got: {ext}")
        sys.exit(1)

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
