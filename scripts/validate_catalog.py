#!/usr/bin/env python3
"""Valida el catálogo estático generado antes de publicarlo."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PIL import Image


REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    html = (REPO / "index.html").read_text(encoding="utf-8")
    match = re.search(r"const productsData = (\[.*?\]);\s*\n", html, re.S)
    if not match:
        raise RuntimeError("No se encontró productsData.")
    products = json.loads(match.group(1))
    if len(products) != 75 or len({product["model"] for product in products}) != 54:
        raise RuntimeError("El inventario publicado no coincide con 75 variantes / 54 modelos.")

    references: set[Path] = set()
    for product in products:
        brand = "flexi" if product["brand"] == "Flexi" else "quirelli"
        references.update(
            REPO / "assets" / brand / "catalogo" / product["model"] / image
            for image in product["images"]
        )
    missing = [path for path in references if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise RuntimeError("Referencias faltantes:\n" + "\n".join(map(str, missing)))

    invalid = []
    for path in sorted(references):
        try:
            with Image.open(path) as image:
                image.verify()
        except Exception as error:
            invalid.append(f"{path}: {error}")
    if invalid:
        raise RuntimeError("Imágenes corruptas:\n" + "\n".join(invalid))

    total_bytes = sum(path.stat().st_size for path in (REPO / "assets").rglob("*.jpg"))
    summary = {
        "inventory_variants": len(products),
        "inventory_models": len({product["model"] for product in products}),
        "referenced_image_paths": len(references),
        "asset_megabytes": round(total_bytes / 1024 / 1024, 2),
        "result": "ok",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Validación fallida: {error}", file=sys.stderr)
        raise
