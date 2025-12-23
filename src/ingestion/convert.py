import pymupdf
import json
from pathlib import Path

RAW_DIR = Path("src/ingestion/data/raw")
OUT_DIR = Path("src/ingestion/data/converted")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def convert_pdf(pdf_path: Path):
    doc = pymupdf.open(pdf_path)
    pages = []

    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text") or ""
        pages.append({
            "page": i + 1,
            "text": text
        })
    
    doc.close()

    out_path = OUT_DIR / f"{pdf_path.stem}.pages.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"source": pdf_path.name, "pages": pages},
            f,
            ensure_ascii=False,
            indent=2
        )
    
def main():
    for pdf in RAW_DIR.glob("*.pdf"):
        convert_pdf(pdf)


if __name__ == "__main__":
    main()