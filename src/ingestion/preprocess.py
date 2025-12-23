import json
import re
from pathlib import Path

IN_DIR = Path("src/ingestion/data/converted")
OUT_DIR = Path("src/ingestion/data/preprocessed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def clean_text(text: str) -> str:
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    lines = [line.strip() for line in text.splitlines()]
    text = " ".join(line for line in lines if line)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def preprocess(file_path: Path):
    data = json.loads(file_path.read_text(encoding="utf-8"))

    cleaned_pages = []
    for p in data["pages"]:
        cleaned_pages.append({
            "page": p["page"],
            "text": clean_text(p["text"])
        })

    out_path = OUT_DIR / file_path.name.replace(".pages.json", ".clean.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"source": data["source"], "pages": cleaned_pages},
            f,
            ensure_ascii=False,
            indent=2
        )

def main():
    for f in IN_DIR.glob("*.pages.json"):
        preprocess(f)

if __name__ == "__main__":
    main()