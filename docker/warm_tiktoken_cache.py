import argparse
import json
import os
import sys

from tiktoken import get_encoding


def parse_args():
    parser = argparse.ArgumentParser(description="Warm and verify tiktoken cache for offline runtime.")
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=os.environ.get("TIKTOKEN_CACHE_DIR", ""),
        help="Target directory for tiktoken cache files.",
    )
    parser.add_argument(
        "--encodings",
        nargs="+",
        default=["o200k_base", "cl100k_base"],
        help="Encoding names to warm.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.cache_dir:
        print("Missing --cache-dir and TIKTOKEN_CACHE_DIR is not set.", file=sys.stderr)
        return 2

    cache_dir = os.path.abspath(os.path.expanduser(args.cache_dir))
    os.makedirs(cache_dir, exist_ok=True)
    os.environ["TIKTOKEN_CACHE_DIR"] = cache_dir

    warmed = []
    for encoding_name in args.encodings:
        get_encoding(encoding_name)
        warmed.append(encoding_name)

    manifest_path = os.path.join(cache_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as manifest_file:
        json.dump({"encodings": warmed}, manifest_file)

    print(f"Tokenizer cache warmed at: {cache_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
