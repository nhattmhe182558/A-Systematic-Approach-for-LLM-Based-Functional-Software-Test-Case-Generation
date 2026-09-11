"""
make_4lv_pdf.py  (Track C input prep)
=====================================

Render the RetailOnboardPro / 4LV SRS (baseline_3/input/srs_extracted_4lv.json)
into a text PDF the IntelliTest pipeline can ingest via pypdf.

NOTE: this JSON is a SMALL SAMPLE (2 use cases) — it is NOT the full
RetailOnboardPro SRS described in the thesis (10 UCs / 8 screens / 75 rules).
The generated PDF is faithful to whatever the JSON contains; downstream results
on this input must be reported as a LIMITED SAMPLE, not a thesis reproduction.
"""
import json
from pathlib import Path

from fpdf import FPDF

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "baseline_3" / "input" / "srs_extracted_4lv.json"
OUT = Path(__file__).resolve().parent / "input_4lv" / "retailonboardpro_4lv_sample.pdf"


def clean(s: str) -> str:
    # fpdf core fonts are latin-1; drop anything outside it.
    return str(s).encode("latin-1", "replace").decode("latin-1")


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    OUT.parent.mkdir(parents=True, exist_ok=True)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    W = pdf.epw  # effective page width (avoids "width 0" rendering bug)
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(W, 10, clean(data.get("project_name", "Software Requirements Specification")))
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(W, 6, clean("Software Requirements Specification (extracted use-case sample). "
                               "Functional test basis: use cases, flows, pre/post-conditions, exceptions."))
    pdf.ln(4)

    for uc in data.get("use_cases", []):
        pdf.set_font("Helvetica", "B", 13)
        pdf.multi_cell(W, 8, clean(f"{uc.get('id','')}: {uc.get('name','')}"))
        pdf.set_font("Helvetica", "", 11)

        def block(label, value):
            if not value:
                return
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(W, 6, clean(label))
            pdf.set_font("Helvetica", "", 11)
            if isinstance(value, list):
                for item in value:
                    pdf.multi_cell(W, 6, clean(f"   - {item}"))
            else:
                pdf.multi_cell(W, 6, clean(f"   {value}"))

        block("Description:", uc.get("description"))
        block("Preconditions:", uc.get("preconditions"))
        block("Normal Flow:", uc.get("normal_flow"))
        block("Alternative Flows:", uc.get("alternative_flows"))
        block("Exceptions:", uc.get("exceptions"))
        block("Postconditions:", uc.get("postconditions"))
        block("Expected Results:", uc.get("expected_results"))
        pdf.ln(3)

    pdf.output(str(OUT))
    print(f"Wrote {OUT}")
    print(f"Use cases rendered: {len(data.get('use_cases', []))}")


if __name__ == "__main__":
    main()
