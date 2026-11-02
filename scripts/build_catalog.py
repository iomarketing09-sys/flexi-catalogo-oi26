#!/usr/bin/env python3
"""Construye la copia pública del catálogo Flexi OI26 desde Google Drive.

No modifica el Growth OS ni los archivos fuente de Drive. Genera `index.html`
y sus imágenes optimizadas dentro de este repositorio de publicación.
"""

from __future__ import annotations

import io
import json
import os
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
FLEXI_OI26 = DRIVE / "marketing/Flexi/Campaña OI26/FOTOS OI26 FINALES"
QUIRELLI_OI26 = DRIVE / "marketing/Quirelli/Campaña OI26/Campaña"
COUNTRY = DRIVE / "marketing/Flexi/Campaña Country OI26/- PORTADILLAS OI26"
CATALOG_DRIVE = DRIVE / "Catalogo"
MISSING = CATALOG_DRIVE / "assets faltantes "
NEW_OI26 = CATALOG_DRIVE / "Assets Faltantes Campaña OI26"
CLASSIC = CATALOG_DRIVE / "Assets Flexi Linea Clasica"
BRANCH_PHOTOS = (
    Path("/tmp/flexi_branch_photos")
    if Path("/tmp/flexi_branch_photos").is_dir()
    else CATALOG_DRIVE / "01_Nov_26 - Assets Faltantes (fotos sucursal)"
)
SURTIDO = (
    Path("/tmp/flexi_surtido")
    if Path("/tmp/flexi_surtido").is_dir()
    else CATALOG_DRIVE / "28_Oct_26 - Surtido"
)

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
EIGHT_VIEW_ORDER = (
    "ARRIBA",
    "ABAJO",
    "IZQ",
    "DER",
    "LATERAL",
    "INTERIOR",
    "ADELANTE",
    "ATRAS",
)
SURTIDO_ORDER = (
    "ADELANTE",
    "ATRAS",
    "IZQ",
    "DER",
    "LATERAL",
    "EXTERIOR",
    "INTERIOR",
    "ARRIBA_PAR",
    "ABAJO_PAR",
    "DER_PAR",
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


def add_zip_series(
    images: dict[tuple[str, str], dict[str, Path | bytes]],
    brand: str,
    model: str,
    color: str,
    archive: Path,
    angles: tuple[str, ...] = ANGLE_ORDER,
) -> None:
    for number, angle in enumerate(angles, start=1):
        add_path(images, brand, model, f"{model}_{color}_{number}.jpg", image_bytes_from_zip(archive, angle))


def folder_photos(folder: Path) -> list[Path]:
    if not folder.is_dir():
        raise FileNotFoundError(folder)
    return sorted(
        path
        for path in folder.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".jpg", ".jpeg", ".png"}
        and "__MACOSX" not in path.parts
        and not path.name.startswith("._")
    )


def add_folder_series(
    images: dict[tuple[str, str], dict[str, Path | bytes]],
    brand: str,
    model: str,
    color: str,
    folder: Path,
    *,
    sources: list[Path] | None = None,
) -> None:
    files = list(sources) if sources is not None else folder_photos(folder)
    for number, source in enumerate(files, start=1):
        add_path(images, brand, model, f"{model}_{color}_{number}.jpg", source)


def add_surtido_series(
    images: dict[tuple[str, str], dict[str, Path | bytes]],
    brand: str,
    model: str,
    color: str,
    folder: Path,
) -> None:
    by_angle: dict[str, Path] = {}
    for source in folder_photos(folder):
        stem = source.stem.upper()
        for angle in SURTIDO_ORDER:
            if stem.endswith(f"_{angle}"):
                by_angle[angle] = source
                break
    number = 1
    for angle in SURTIDO_ORDER:
        source = by_angle.get(angle)
        if source is not None:
            add_path(images, brand, model, f"{model}_{color}_{number}.jpg", source)
            number += 1


def source_images() -> dict[tuple[str, str], dict[str, Path | bytes]]:
    if os.getenv("FLEXI_INCREMENTAL") == "1":
        images: dict[tuple[str, str], dict[str, Path | bytes]] = {}
        add_branch_photos(images)
        add_surtido_photos(images)
        return images

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
        ("Flexi", "101912", "negro", NEW_OI26 / "101912_NEGRO.zip"),
        ("Flexi", "117207", "negro", NEW_OI26 / "117207_NEGRO.zip", EIGHT_VIEW_ORDER),
        ("Flexi", "117207", "taupe", NEW_OI26 / "117207_TAUPE.zip"),
        ("Flexi", "134806", "negro", NEW_OI26 / "134806_BLACK-20260706T215338Z-3-001.zip"),
        ("Flexi", "136804", "negro", NEW_OI26 / "136804_NEGRO.zip"),
        ("Flexi", "137002", "oro_rosado", NEW_OI26 / "137002_ORO_ROSADO.zip"),
        ("Flexi", "140601", "oro_rosado", NEW_OI26 / "140601_ORO_ROSA-20260106T221544Z-3-001.zip"),
        ("Flexi", "142303", "negro", NEW_OI26 / "142303_NEGRO-20260706T215845Z-3-001.zip"),
        ("Flexi", "406401", "tan", CLASSIC / "406401_TAN-20260105T171526Z-3-001.zip"),
        ("Flexi", "406412", "negro", CLASSIC / "406412_NEGRO.zip"),
        ("Flexi", "407801", "tan", CLASSIC / "407801_TAN.zip"),
        ("Flexi", "417606", "negro", CLASSIC / "417606_NEGRO.zip"),
        ("Flexi", "417606", "taupe", CLASSIC / "417606_TAUPE.zip"),
        ("Flexi", "421501", "tinto", CLASSIC / "421501_TINTO-20260105T181604Z-3-001.zip"),
        ("Flexi", "421503", "tan", CLASSIC / "421503_TAN-20260105T181607Z-3-001.zip"),
        ("Flexi", "422906", "tan", CLASSIC / "422906_TAN-20260105T192545Z-3-001.zip"),
        ("Flexi", "423101", "cognac", CLASSIC / "423101_COGNAC-20260105T192554Z-3-001.zip"),
        ("Flexi", "423101", "negro", CLASSIC / "423101_NEGRO-20260105T192555Z-3-001.zip"),
        ("Flexi", "423201", "negro", CLASSIC / "423201_NEGRO-20260105T194353Z-3-001.zip"),
        ("Flexi", "424202", "azul", CLASSIC / "424202_AZUL-20260105T214644Z-3-001.zip"),
        ("Flexi", "424202", "negro", CLASSIC / "424202_NEGRO-20260105T214713Z-3-001.zip"),
        ("Flexi", "424601", "blanco", CLASSIC / "424601_WHITE-20260702T232556Z-3-001.zip"),
    )
    for spec in archive_specs:
        brand, model, color, archive, *optional_angles = spec
        angles = optional_angles[0] if optional_angles else ANGLE_ORDER
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
            add_zip_series(images, brand, model, color, archive, angles)

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

    add_branch_photos(images)
    add_surtido_photos(images)
    return images


def add_branch_photos(images: dict[tuple[str, str], dict[str, Path | bytes]]) -> None:
    add_folder_series(images, "Flexi", "101905", "tan", BRANCH_PHOTOS / "101905 - Cafe")
    add_folder_series(images, "Flexi", "101905", "negro", BRANCH_PHOTOS / "101905 - Negro")

    amelia = BRANCH_PHOTOS / "101908 - Negro y Cafe"
    amelia_files = folder_photos(amelia)
    add_folder_series(images, "Flexi", "101908", "cafe", amelia, sources=amelia_files[:3])
    add_folder_series(images, "Flexi", "101908", "negro", amelia, sources=amelia_files[3:])

    add_folder_series(images, "Flexi", "402112", "negro", BRANCH_PHOTOS / "402112 - Negro")
    add_folder_series(images, "Flexi", "404801", "oporto", BRANCH_PHOTOS / "404801 - Cafe")
    add_folder_series(images, "Flexi", "404801", "negro", BRANCH_PHOTOS / "404801 - Negro")
    add_folder_series(images, "Flexi", "414404", "negro", BRANCH_PHOTOS / "414404 - Negro")
    add_folder_series(images, "Flexi", "48301", "negro", BRANCH_PHOTOS / "48301 - Negro")
    add_folder_series(images, "Flexi", "48303", "negro", BRANCH_PHOTOS / "48303 - Negro")
    add_folder_series(images, "Flexi", "5807", "blanco", BRANCH_PHOTOS / "5807 - Blanco")
    add_folder_series(images, "Flexi", "50816", "negro", BRANCH_PHOTOS / "58016 - Negro")

    quilmes = BRANCH_PHOTOS / "59305 - Cafe y Negro"
    add_folder_series(
        images, "Flexi", "59305", "dk_oporto", quilmes, sources=folder_photos(quilmes)[:4]
    )

    add_folder_series(images, "Flexi", "63201", "blanco", BRANCH_PHOTOS / "63201 - Blanco")
    add_folder_series(images, "Flexi", "63202", "blanco", BRANCH_PHOTOS / "63202")
    add_folder_series(
        images,
        "Flexi",
        "66514",
        "chocolate",
        BRANCH_PHOTOS / "66514 - Cafe (flexi country)",
    )
    add_folder_series(images, "Quirelli", "700804", "negro", BRANCH_PHOTOS / "700804 - Negro")
    add_folder_series(images, "Quirelli", "700803", "cafe", BRANCH_PHOTOS / "700803 - Cafe")
    add_folder_series(images, "Quirelli", "88701", "negro", BRANCH_PHOTOS / "88701 - Negro")

    mocasin = BRANCH_PHOTOS / "88702 - Negro y Cafe"
    mocasin_files = folder_photos(mocasin)
    add_folder_series(images, "Quirelli", "88702", "brandy", mocasin, sources=mocasin_files[:3])
    add_folder_series(images, "Quirelli", "88702", "negro", mocasin, sources=mocasin_files[3:])


def add_surtido_photos(images: dict[tuple[str, str], dict[str, Path | bytes]]) -> None:
    specs = (
        ("Flexi", "104529", "negro", "104529_NEGRO"),
        ("Flexi", "104834", "negro", "104834_NEGRO"),
        ("Flexi", "137503", "negro", "137503_NEGRO"),
        ("Flexi", "137511", "negro", "137511_NEGRO"),
        ("Flexi", "142302", "cafe", "142302_CAFE"),
        ("Flexi", "142302", "negro", "142302_NEGRO"),
        ("Flexi", "142601", "tan", "142601_TAN"),
        ("Quirelli", "307001", "black", "307001_BLACK"),
        ("Quirelli", "307001", "taupe", "307001_TAUPE"),
        ("Quirelli", "307103", "negro", "307103_NEGRO"),
        ("Flexi", "37830", "negro", "37830_NEGRO"),
    )
    for brand, model, color, folder in specs:
        add_surtido_series(images, brand, model, color, SURTIDO / folder)


def update_products(source: str) -> tuple[str, list[dict[str, object]]]:
    match = re.search(r"const productsData = (\[.*?\]);\s*\n", source, re.S)
    if not match:
        raise RuntimeError("No se encontró productsData en el HTML fuente.")
    products = json.loads(match.group(1))
    product_image_overrides = {
        ("Flexi", "418502"): product_images("418502", "negro"),
        ("Flexi", "101912", "Negro"): product_images("101912", "negro"),
        ("Flexi", "117207", "Negro"): product_images("117207", "negro", 8),
        ("Flexi", "117207", "Taupe"): product_images("117207", "taupe"),
        ("Flexi", "134806", "Negro"): product_images("134806", "negro"),
        ("Flexi", "136804", "Negro"): product_images("136804", "negro"),
        ("Flexi", "137002", "Oro rosado"): product_images("137002", "oro_rosado"),
        ("Flexi", "140601", "Oro rosado"): product_images("140601", "oro_rosado"),
        ("Flexi", "142303", "Negro"): product_images("142303", "negro"),
        ("Flexi", "406401", "Tan"): product_images("406401", "tan"),
        ("Flexi", "406412", "Negro"): product_images("406412", "negro"),
        ("Flexi", "407801", "Tan"): product_images("407801", "tan"),
        ("Flexi", "417606", "Negro"): product_images("417606", "negro"),
        ("Flexi", "417606", "Taupe"): product_images("417606", "taupe"),
        ("Flexi", "421501", "Tinto"): product_images("421501", "tinto"),
        ("Flexi", "421503", "Tan"): product_images("421503", "tan"),
        ("Flexi", "422906", "Tan"): product_images("422906", "tan"),
        ("Flexi", "423101", "Cognac"): product_images("423101", "cognac"),
        ("Flexi", "423101", "Negro"): product_images("423101", "negro"),
        ("Flexi", "423201", "Negro"): product_images("423201", "negro"),
        ("Flexi", "424202", "Azul"): product_images("424202", "azul"),
        ("Flexi", "424202", "Negro"): product_images("424202", "negro"),
        ("Flexi", "424601", "Blanco"): product_images("424601", "blanco"),
        ("Flexi", "101905", "Tan"): product_images("101905", "tan", 3),
        ("Flexi", "101905", "Negro"): product_images("101905", "negro", 4),
        ("Flexi", "101908", "Café"): product_images("101908", "cafe", 3),
        ("Flexi", "101908", "Negro"): product_images("101908", "negro", 4),
        ("Flexi", "402112", "Negro"): product_images("402112", "negro", 4),
        ("Flexi", "404801", "Oporto"): product_images("404801", "oporto", 5),
        ("Flexi", "404801", "Negro"): product_images("404801", "negro", 4),
        ("Flexi", "414404", "Negro"): product_images("414404", "negro", 4),
        ("Flexi", "48301", "Negro"): product_images("48301", "negro", 4),
        ("Flexi", "48303", "Negro"): product_images("48303", "negro", 4),
        ("Flexi", "5807", "Blanco"): product_images("5807", "blanco", 4),
        ("Flexi", "50816", "Negro"): product_images("50816", "negro", 5),
        ("Flexi", "59305", "DK Oporto"): product_images("59305", "dk_oporto", 4),
        ("Flexi", "63201", "Blanco"): product_images("63201", "blanco", 4),
        ("Flexi", "63202", "Blanco"): product_images("63202", "blanco", 5),
        ("Flexi", "66514", "Chocolate"): product_images("66514", "chocolate", 4),
        ("Quirelli", "700804", "Negro"): product_images("700804", "negro", 3),
        ("Quirelli", "700803", "Café"): product_images("700803", "cafe", 2),
        ("Quirelli", "88701", "Negro"): product_images("88701", "negro", 3),
        ("Quirelli", "88702", "Brandy"): product_images("88702", "brandy", 3),
        ("Quirelli", "88702", "Negro"): product_images("88702", "negro", 6),
        ("Flexi", "104529", "Negro"): product_images("104529", "negro", 10),
        ("Flexi", "104834", "Negro"): product_images("104834", "negro", 10),
        ("Flexi", "137503", "Negro"): product_images("137503", "negro", 9),
        ("Flexi", "137511", "Negro"): product_images("137511", "negro", 10),
        ("Flexi", "142302", "Café"): product_images("142302", "cafe", 10),
        ("Flexi", "142302", "Negro"): product_images("142302", "negro", 10),
        ("Flexi", "142601", "Tan"): product_images("142601", "tan", 10),
        ("Quirelli", "307001", "Black"): product_images("307001", "black", 10),
        ("Quirelli", "307001", "Taupe"): product_images("307001", "taupe", 10),
        ("Quirelli", "307103", "Negro"): product_images("307103", "negro", 10),
        ("Flexi", "37830", "Negro"): product_images("37830", "negro", 10),
    }
    for product in products:
        override = product_image_overrides.get((product["brand"], product["model"], product["color"]))
        if override is None:
            override = product_image_overrides.get((product["brand"], product["model"]))
        if override:
            product["has_images"] = True
            product["images"] = override
    replacement = f"const productsData = {json.dumps(products, ensure_ascii=False)};\n"
    output = source[:match.start()] + replacement + source[match.end():]
    return apply_model_grouping(output), products


def apply_model_grouping(html: str) -> str:
    """Presenta una tarjeta por modelo sin cambiar las variantes fuente."""
    grouping = '''const catalogProducts = Object.values(productsData.reduce((groups, product) => {
            const key = `${product.brand}:${product.model}`;
            const grouped = groups[key] || {
                ...product,
                colors: [],
                images: [],
                has_images: false,
            };
            if (!grouped.colors.includes(product.color)) grouped.colors.push(product.color);
            product.images.forEach((image) => {
                if (!grouped.images.includes(image)) grouped.images.push(image);
            });
            grouped.has_images = grouped.images.length > 0;
            groups[key] = grouped;
            return groups;
        }, {}));
        '''
    anchor = '        const STORE_WHATSAPP = "5218781385284";'
    if anchor not in html:
        raise RuntimeError("No se encontró el punto de inserción para agrupar el catálogo.")
    html = html.replace(anchor, f"        {grouping}\n{anchor}", 1)

    replacements = (
        ("card.dataset.color = item.color.toLowerCase();", "card.dataset.color = item.colors.join(' ').toLowerCase();"),
        ("getShoeSvg(item.category, item.color)", "getShoeSvg(item.category, item.colors[0])"),
        ("const modelColors = [...new Set(productsData.filter(p => p.model === item.model).map(p => p.color))];", "const modelColors = item.colors;"),
        ("Hola, me interesa comprar el modelo ${item.brand} ${item.name} (${item.model}) en color ${item.color} que vi en el Catálogo de Piedras Negras.", "Hola, me interesa comprar el modelo ${item.brand} ${item.name} (${item.model}) que vi en el Catálogo de Piedras Negras. ¿Me comparten disponibilidad y colores?"),
        ("const filtered = productsData.filter(item => {", "const filtered = catalogProducts.filter(item => {"),
        ("item.color.toLowerCase().includes(query);", "item.colors.some(color => color.toLowerCase().includes(query));"),
        ("resultsCount.textContent = `${count} producto${count !== 1 ? 's' : ''} encontrado${count !== 1 ? 's' : ''}`;", "resultsCount.textContent = `${count} modelo${count !== 1 ? 's' : ''} encontrado${count !== 1 ? 's' : ''}`;"),
        ("`SKU: ${item.model} • Color: ${item.color}`", "`SKU: ${item.model} • ${item.colors.length} color${item.colors.length !== 1 ? 'es' : ''} disponible${item.colors.length !== 1 ? 's' : ''}`"),
        ("<div class=\"detail-row\"><span class=\"detail-label\">Color</span><span class=\"detail-value\">${item.color}</span></div>", "<div class=\"detail-row\"><span class=\"detail-label\">Colores</span><span class=\"detail-value\">${item.colors.join(', ')}</span></div>"),
    )
    for old, new in replacements:
        count = html.count(old)
        if count == 0:
            raise RuntimeError(f"No se encontró el fragmento para actualizar: {old}")
        html = html.replace(old, new)

    old_colors = '''<span class="colors-label">Colores del modelo:</span>
                            ${swatchesHtml}'''
    new_colors = '''<span class="colors-label">Colores en inventario:</span>
                            ${swatchesHtml}
                            <span style="font-size:0.72rem; color:#64748B; margin-left:0.35rem;">${modelColors.join(' · ')}</span>'''
    if old_colors not in html:
        raise RuntimeError("No se encontró la sección de colores de la tarjeta.")
    return apply_modal_presentation(html.replace(old_colors, new_colors))


def apply_modal_presentation(html: str) -> str:
    """Mantiene la ficha compacta y usable en móvil."""
    replacements = (
        (
            "        @media (max-width: 768px) {\n            .modal-grid { grid-template-columns: 1fr; }\n        }",
            "        @media (max-width: 768px) {\n            .modal-grid { grid-template-columns: 1fr; gap: 1.25rem; }\n            .modal-content { max-height: 94vh; width: 94%; margin: 3vh auto; }\n            .modal-body { padding: 1rem; }\n            .modal-header { padding: 1rem 1.25rem; }\n            .modal-image-main { max-height: 50vh; }\n            .modal-image-placeholder { max-height: 50vh; }\n        }",
        ),
        (
            "        .modal-image-main {\n            width: 100%;\n            aspect-ratio: 3/4;\n            object-fit: cover;",
            "        .modal-image-main {\n            width: 100%;\n            max-height: 68vh;\n            aspect-ratio: 4/5;\n            object-fit: contain;",
        ),
        (
            "        .modal-image-placeholder {\n            width: 100%;\n            aspect-ratio: 3/4;",
            "        .modal-image-placeholder {\n            width: 100%;\n            max-height: 68vh;\n            aspect-ratio: 4/5;",
        ),
        (
            "<div class=\"modal-thumbnails\" id=\"modalThumbnails\"></div>",
            "<div class=\"modal-thumbnails\" id=\"modalThumbnails\" data-max=\"5\"></div>",
        ),
        (
            "thumbnails.innerHTML = item.images.map((img, idx) => {",
            "const limitedImages = item.images.slice(0, 5);\n                thumbnails.innerHTML = limitedImages.map((img, idx) => {",
        ),
        (
            "            const src = `assets/${marcaPath}/catalogo/${model}/${productsData.find(p => p.model === model && p.color === thumb.alt.split(' ').pop()).images[index]}`;\n            // Actually we need the correct image - let's use the thumb's src\n            document.getElementById('modalMainImage').src = thumb.src;",
            "            document.getElementById('modalMainImage').src = thumb.src;",
        ),
    )
    for old, new in replacements:
        if old not in html:
            raise RuntimeError(f"No se encontró el fragmento del modal: {old}")
        html = html.replace(old, new, 1)
    return html


def build() -> None:
    print("Leyendo fuentes...", flush=True)
    image_sources = source_images()
    source = SOURCE_HTML.read_text(encoding="utf-8")
    print("Actualizando catálogo...", flush=True)
    output_html, products = update_products(source)
    (REPO / "index.html").write_text(output_html, encoding="utf-8")
    shutil.copy2(SOURCE_SEAL, REPO / SOURCE_SEAL.name)

    assets = REPO / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    total = sum(len(files) for files in image_sources.values())
    done = 0
    for (brand, model), files in image_sources.items():
        for name, source_file in files.items():
            destination = REPO / rel_asset_path(brand, model, name)
            if not (destination.exists() and destination.stat().st_size > 0):
                write_optimized(destination, source_file)
            done += 1
            if done % 25 == 0 or done == total:
                print(f"Imágenes: {done}/{total}", flush=True)

    referenced = []
    for product in products:
        brand = product["brand"]
        model = product["model"]
        for filename in product["images"]:
            referenced.append(REPO / rel_asset_path(brand, model, filename))
    summary = {
        "inventory_variants": len(products),
        "inventory_models": len({product["model"] for product in products}),
        "published_cards": len({product["model"] for product in products}),
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
