"""Build browser-readable evidence from actual executed notebook stdout.

Screenshots are captured from these pages; no metrics are manually entered.
"""
from __future__ import annotations

import hashlib
import html
from pathlib import Path
import re

import nbformat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "submission" / "evidence"
SPECS = {
    "01": ("NB1 · 1.000 vectors & similarity search", ["n_indexed =", 'query = "cloud', "query2 ="]),
    "02": ("NB2 · Precision@10 trên 50 queries", ["p_kw, p_sem", "by_type:"]),
    "03": ("NB3 · FastAPI & server-side latency", ["body = r.json()", "def benchmark_mode", "hybrid_p99 ="]),
    "04": ("NB4 · Feast, SQLite & Point-in-Time", ["[\"feast\", \"apply\"]", "end_dt =", "REQUEST_FEATURES =", "latencies: list", "entity_df ="]),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for number, (title, markers) in SPECS.items():
        path = next((ROOT / "notebooks").glob(f"{number}_*.ipynb"))
        notebook = nbformat.read(path, as_version=4)
        cards = []
        for cell in notebook.cells:
            if cell.cell_type != "code" or not any(m in cell.source for m in markers):
                continue
            assert cell.execution_count is not None, f"Unexecuted evidence cell in {path}"
            assert not any(o.output_type == "error" for o in cell.outputs), path
            stdout = "".join(o.text for o in cell.outputs
                             if o.output_type == "stream" and o.name == "stdout")
            stdout = re.sub(r"\x1b\[[0-9;]*m", "", stdout).strip()
            if number == "04" and '["feast", "apply"]' in cell.source:
                stdout = "\n".join(line for line in stdout.splitlines()
                                   if "Created feature view" in line
                                   or ("FeatureView" in line and "features" in line))
            stdout = "\n".join(line for line in stdout.splitlines() if line.strip())
            if not stdout:
                continue
            cards.append(f'<section><label>In [{cell.execution_count}] · stdout</label>'
                         f'<pre>{html.escape(stdout)}</pre></section>')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        document = f'''<!doctype html><html lang="vi"><meta charset="utf-8">
<title>{html.escape(title)}</title><style>
*{{box-sizing:border-box}} body{{margin:0;background:#f3f6fa;color:#14243b;font:14px 'Segoe UI',sans-serif}}
main{{max-width:1440px;margin:auto;padding:24px}} h1{{margin:4px 0 8px;font-size:27px}}
.meta{{color:#48617d;margin-bottom:18px}} .grid{{display:grid;gap:12px}}
section{{background:white;border:1px solid #d4deeb;border-radius:8px;padding:14px}}
label{{font-size:12px;color:#386382;font-weight:600}} pre{{font:13px/1.45 Consolas,'Courier New',monospace;white-space:pre-wrap;overflow-wrap:anywhere;margin:8px 0 0}}
footer{{font-size:11px;color:#586b83;margin-top:12px;overflow-wrap:anywhere}}
body.nb04 .grid{{grid-template-columns:1fr 1fr}} body.nb04 section:first-child{{grid-row:span 2}}
body.nb04 pre{{font-size:12px;line-height:1.35}}
@media(max-width:500px){{
main{{padding:10px}} h1{{font-size:17px}} .meta{{font-size:10px;margin-bottom:8px}}
.grid{{gap:6px}} section{{padding:7px}} label{{font-size:8px}}
pre,body.nb04 pre{{font-size:9px;line-height:1.3;margin-top:4px}}
body.nb04 pre{{font-size:8px;line-height:1.2}}
body.nb04 .grid{{grid-template-columns:1fr}} body.nb04 section:first-child{{grid-row:auto}}
footer{{font-size:7px;line-height:1.3;margin-top:8px}}
}}
</style><body class="nb{number}"><main><div class="meta">LÊ VĂN SANG · K4 TRACK 2 · LAB 19 · LITE</div>
<h1>{html.escape(title)}</h1><div class="meta">Trích đoạn stdout từ notebook đã thực thi: {path.name}</div>
<div class="grid">{''.join(cards)}</div>
<footer>Source SHA-256: {digest}<br>Ảnh minh chứng chụp từ trang hiển thị output này; toàn bộ code/output nằm trong notebook.</footer>
</main></body></html>'''
        (OUT / f"nb{number}.html").write_text(document, encoding="utf-8")
        print(f"Built {OUT / f'nb{number}.html'}")


if __name__ == "__main__":
    main()
