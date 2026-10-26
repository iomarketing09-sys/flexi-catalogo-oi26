#!/usr/bin/env python3
"""Construye la copia pública del catálogo Flexi OI26 desde Google Drive.

No modifica el Growth OS ni los archivos fuente de Drive. Genera `index.html`
y sus imágenes optimizadas dentro de este repositorio de publicación.
"""

from __future__ import annotations

import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageOps


REPO = Path(__file__).resolve().parents[1]
GROWTH_OS = REPO.parent
SOURCE_HTML = GROWTH_OS / "tenants/flexi/catalogo_flexi_oi26_enriquecido.html"
SOURCE_SEAL = GROWTH_OS / "tenants/flexi/sello_dorado_oi26.svg"
DRIVE = Path("/home/universe-sent-me/GoogleDrive/Informes FLEXI")
MISSING = DRIVE / "assets faltantes "
FLEXI_OI26 = DRIVE / "marketing/Flexi/Campaña OI26/FOTOS OI26 FINALES"
QUIRELLI_OI26 = DRIVE / "marketing/Quirelli/Campaña OI26/Campaña"
COUNTRY = DRIVE / "marketing/Flexi/Campaña Country OI26/- PORTADILLAS OI26"

ANGLE_ORDER = (
    "ARRIBA_PAR",
    "ABAJO_PAR",
    "DER_PAR",
    "IZQ",
    "DER",
    "LATERAL",
    "INTERIOR",
    "ADELANTE",
    "ATRAS",
)


def rel_asset_path(brand: str, model: str, filename: str) -> Path:
    brand_path = "flexi" if brand == "Flexi" else "quirelli"
    return Path("assets") / brand_path / "catalogo" / model / filename


def product_images(model: str, color: str, count: int = 9) -> list[str]:
    suffix = color.lower().replace(" ", "_")
    return [f"{model}_{suffix}_{number}.jpg" for number in range(1, count + 1)]


def image_bytes_from_zip(archive: Path, token: str) -> bytes:
    pattern = re.compile(rf"_{re.escape(token.upper())}\.(?:jpe?g)$", re.IGNORECASE)
    with zipfile.ZipFile(archive) as bundle:
        candidates = [
            name for name in bundle.namelist()
            if name.lower().endswith((".jpg", ".jpeg")) and "__MACOSX" not in name and pattern.search(name)
        ]
        if len(candidates) != 1:
            raise RuntimeError(f"No se encontró una foto única para {token} en {archive.name}: {candidates}")
        return bundle.read(candidates[0])


def write_optimized(destination: Path, source: Path | bytes) -> None:
    data = source.read_bytes() if isinstance(source, Path) else source
    with Image.open(io.BytesIO(data)) as raw:
        image = ImageOps.exif_transpose(raw).convert("RGB")
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, "JPEG", quality=82, optimize=True, progressive=True)


def add_path(images: dict[tuple[str, str], dict[str, Path | bytes]], brand: str, model: str, name: str, source: Path | bytes) -> None:
    images.setdefault((brand, model), {})[name] = source


def add_zip_series(images: dict[tuple[str, str], dict[str, Path | bytes]], brand: str, model: str, color: str, archive: Path) -> None:
    for number, angle in enumerate(ANGLE_ORDER, start=1):
        add_path(images, brand, model, f"{model}_{color}_{number}.jpg", image_bytes_from_zip(archive, angle))


def source_images() -> dict[tuple[str, str], dict[str, Path | bytes]]:
    images: dict[tuple[str, str], dict[str, Path | bytes]] = {}

    direct = {
        ("Flexi", "142801"): {
            "142801_beige.jpg": FLEXI_OI26 / "ISAURA_142801_BEIGE_OI26.JPG",
            "142801_tan.jpg": FLEXI_OI26 / "ISAURA_142801_TAN_OI26.JPG",
        },
        ("Flexi", "142901"): {
            "142901_tan.jpg": FLEXI_OI26 / "JOCELYN_142901_TAN_OI26.jpg",
        },
        ("Flexi", "143001"): {
            "143001_plata.jpg": FLEXI_OI26 / "GINNY_143001_PLATA_OI26.jpg",
        },
        ("Flexi", "143201"): {
            "143201_beige.jpg": FLEXI_OI26 / "LYDIA_143201_VIBORA BEIGE_OI26.JPG",
            "143201_negro.jpg": FLEXI_OI26 / "LYDIA_143201_NEGRO_OI26.jpg",
        },
        ("Flexi", "401001"): {
            "401001_tan.jpg": COUNTRY / "RANDALL_401001_TAN／EPIC_406003_BRANDY_05838.jpg",
        },
        ("Flexi", "66517"): {
            "66517_negro_1.jpg": COUNTRY / "FREELAND_66517_NEGRO_02133.jpg",
            "66517_negro_2.jpg": COUNTRY / "FREELAND_66517_NEGRO_02239.JPG",
        },
        ("Flexi", "66525"): {
            "66525_chocolate_1.jpg": COUNTRY / "FREELAND_66525_CHOCOLATE_01956.jpg",
            "66525_chocolate_2.jpg": COUNTRY / "FREELAND_66525_CHOCOLATE_02048.JPG",
            "66525_negro_1.jpg": COUNTRY / "FREELAND_66525_NEGRO_02300.jpg",
            "66525_negro_2.jpg": COUNTRY / "FREELAND_66525_NEGRO_02352.jpg",
            "66525_negro_3.jpg": COUNTRY / "FREELAND_66525_NEGRO_02371.jpg",
        },
    }
    for key, files in direct.items():
        for name, source in files.items():
            if not source.exists():
                raise FileNotFoundError(source)
            add_path(images, *key, name, source)

    archive_specs = (
        ("Flexi", "127202", "negro", MISSING / "127202_NEGRO.zip"),
        ("Flexi", "139601", "oro", MISSING / "139601_ORO-20260106T194018Z-3-001.zip"),
        ("Quirelli", "304402", "latte", MISSING / "304402_LATTE.zip"),
        ("Quirelli", "304402", "negro", MISSING / "304402_NEGRO.zip"),
        ("Quirelli", "305101", "negro", MISSING / "305101_NEGRO.zip"),
        ("Quirelli", "305101", "tan", MISSING / "305101_TAN.zip"),
        ("Flexi", "403019", "beige", MISSING / "403019_BEIGE-20260105T171506Z-3-001.zip"),
        ("Flexi", "418502", "negro", MISSING / "418502_NEGRO.zip"),
        ("Flexi", "419501", "tan", MISSING / "419501_TAN.zip"),
        ("Flexi", "419502", "negro", MISSING / "419502_NEGRO.zip"),
        ("Flexi", "423803", "marino", MISSING / "423803_MARINO-20260105T195709Z-3-001.zip"),
        ("Quirelli", "707205", "negro", MISSING / "707205_NEGRO-20260105T162309Z-3-001.zip"),
        ("Quirelli", "707902", "negro", MISSING / "707902_NEGRO.zip"),
    )
    for brand, model, color, archive in archive_specs:
        if model == "127202":
            # Las fotos de este modelo llegaron descomprimidas.
            folder = MISSING / "127202_NEGRO"
            if not folder.is_dir():
                raise FileNotFoundError(folder)
            for number, angle in enumerate(ANGLE_ORDER, start=1):
                source = folder / f"127202_NEGRO_{angle}.jpg"
                add_path(images, brand, model, f"127202_negro_{number}.jpg", source)
        else:
            if not archive.exists():
                raise FileNotFoundError(archive)
            add_zip_series(images, brand, model, color, archive)

    arisha = {
        "306703_negro_1.jpg": QUIRELLI_OI26 / "ARISHA_306703_NEGRO_QUIRELLI_OI26.jpg",
        "306703_negro_2.jpg": QUIRELLI_OI26 / "ARISHA_306703_NEGRO_QUIRELLI_OI26_2.jpg",
        "306703_negro_3.jpg": QUIRELLI_OI26 / "ARISHA_306703_NEGRO_QUIRELLI_OI26_ESTILO DE VIDA.jpg",
        "306703_negro_4.jpg": QUIRELLI_OI26 / "ARISHA_306703_NEGRO_RAFAELLA_1430000855_NEGRO_QUIRELLI_OI26.jpg",
        "306703_negro_5.jpg": QUIRELLI_OI26 / "ARISHA_306703_NEGRO_RAFAELLA_1430000855_NEGRO_QUIRELLI_OI26_2.jpg",
        "306703_nude_1.jpg": QUIRELLI_OI26 / "ARISHA_306703_NUDE_QUIRELLI_OI26.jpg",
        "306703_nude_2.jpg": QUIRELLI_OI26 / "ARISHA_306703_NUDE_QUIRELLI_OI26_ESTILO DE VIDA.jpg",
        "306703_nude_3.jpg": QUIRELLI_OI26 / "ARISHA_306703_NUDE_QUIRELLI_OI26_ESTILO DE VIDA 2.jpg",
        "306703_nude_4.jpg": QUIRELLI_OI26 / "ARISHA_306703_NUDE_QUIRELLI_OI26_ESTILO DE VIDA 3.jpg",
        "306703_nude_5.jpg": QUIRELLI_OI26 / "ARISHA_306703_NUDE_QUIRELLI_OI26_ESTILO DE VIDA 4.jpg",
    }
    for name, source in arisha.items():
        add_path(images, "Quirelli", "306703", name, source)
    return images


def update_products(source: str) -> tuple[str, list[dict[str, object]]]:
    match = re.search(r"const productsData = (\[.*?\]);\s*\n", source, re.S)
    if not match:
        raise RuntimeError("No se encontró productsData en el HTML fuente.")
    products = json.loads(match.group(1))
    product_image_overrides = {
        ("Flexi", "418502"): product_images("418502", "negro"),
    }
    for product in products:
        override = product_image_overrides.get((product["brand"], product["model"]))
        if override:
            product["has_images"] = True
            product["images"] = override
    replacement = f"const productsData = {json.dumps(products, ensure_ascii=False)};\n"
    return source[:match.start()] + replacement + source[match.end():], products


def build() -> None:
    image_sources = source_images()
    source = SOURCE_HTML.read_text(encoding="utf-8")
    output_html, products = update_products(source)
    (REPO / "index.html").write_text(output_html, encoding="utf-8")
    shutil.copy2(SOURCE_SEAL, REPO / SOURCE_SEAL.name)

    assets = REPO / "assets"
    if assets.exists():
        shutil.rmtree(assets)
    for (brand, model), files in image_sources.items():
        for name, source_file in files.items():
            write_optimized(REPO / rel_asset_path(brand, model, name), source_file)

    referenced = []
    for product in products:
        brand = product["brand"]
        model = product["model"]
        for filename in product["images"]:
            referenced.append(REPO / rel_asset_path(brand, model, filename))
    summary = {
        "inventory_variants": len(products),
        "inventory_models": len({product["model"] for product in products}),
        "products_with_real_images": sum(bool(product["images"]) for product in products),
        "referenced_image_paths": len(referenced),
        "unique_referenced_images": len(set(referenced)),
        "generated_images": sum(1 for _ in assets.rglob("*.jpg")),
    }
    (REPO / "build-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        build()
    except Exception as error:
        print(f"Error de construcción: {error}", file=sys.stderr)
        raise
