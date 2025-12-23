import convert
import preprocess
import chunk


def main():
    print("\n=== STEP 1: CONVERT PDF -> PER-PAGE TEXT ===")
    convert.main()

    print("\n=== STEP 2: PREPROCESS TEXT (CLEANING) ===")
    preprocess.main()

    print("\n=== STEP 3: CHUNK TEXT BY LEGAL SECTIONS ===")
    chunk.main()

    print("\n=== INGESTION PIPELINE FINISHED ===")


if __name__ == "__main__":
    main()