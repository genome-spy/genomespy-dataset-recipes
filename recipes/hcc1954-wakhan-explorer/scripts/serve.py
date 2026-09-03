#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Serve the recipe and an existing GenomeSpy Core bundle on localhost."""

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8082)
    parser.add_argument("--genomespy", type=Path, default=ROOT.parents[3])
    args = parser.parse_args()
    bundle = args.genomespy.resolve() / "packages/core/dist/bundle"
    assert (bundle / "index.es.js").is_file(), "Build GenomeSpy Core first"

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=str(ROOT), **kwargs)  # type: ignore[arg-type]

        def translate_path(self, path: str) -> str:
            if path.startswith("/runtime/"):
                relative = Path(path.removeprefix("/runtime/").split("?")[0])
                assert ".." not in relative.parts
                return str(bundle / relative)
            return super().translate_path(path)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"http://127.0.0.1:{args.port}/specs/index.html", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
