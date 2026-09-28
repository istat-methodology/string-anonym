import argparse
import json
from pathlib import Path


def jsonl_to_json(input_path: str, output_path: str) -> None:
    input_file = Path(input_path)
    output_file = Path(output_path)

    records = []

    with input_file.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Errore JSON alla riga {line_number}: {e}"
                ) from e

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(
            records,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Convertiti {len(records)} record.")
    print(f"Output salvato in: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Converti un file JSONL in un JSON leggibile."
    )

    parser.add_argument(
        "input",
        help="Path del file JSONL di input"
    )

    parser.add_argument(
        "output",
        help="Path del file JSON di output"
    )

    args = parser.parse_args()

    jsonl_to_json(args.input, args.output)


if __name__ == "__main__":
    main()