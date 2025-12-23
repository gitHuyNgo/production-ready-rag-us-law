import json
import re
from pathlib import Path

IN_DIR = Path("src/ingestion/data/preprocessed")
OUT_DIR = Path("src/ingestion/data/chunks")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SECTION_RE = re.compile(r"(§\s*\d+[A-Za-z0-9\-]*\.)")


def chunk_sections(text: str):
    parts = SECTION_RE.split(text)
    chunks = []

    for i in range(1, len(parts), 2):
        section_header = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        chunks.append((section_header + body).strip())

    return chunks


def chunk_file(file_path: Path):
    data = json.loads(file_path.read_text(encoding="utf-8"))

    full_text = " ".join(p["text"] for p in data["pages"])
    sections = chunk_sections(full_text)

    out = []
    for s in sections:
        out.append({
            "content": s,
            "source": data["source"]
        })

    out_path = OUT_DIR / file_path.name.replace(".clean.json", ".chunks.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


def main():
    for f in IN_DIR.glob("*.clean.json"):
        chunk_file(f)

if __name__ == "__main__":
    main()