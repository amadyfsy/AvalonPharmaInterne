#!/usr/bin/env python3
"""
Recherche et télécharge des photos produit (sources libres : Wikimedia Commons, Openverse).

Usage (depuis la racine GestAvalon) :
  python sql/fetch_produit_photos.py --dry-run
  python sql/fetch_produit_photos.py --apply-db
  python sql/fetch_produit_photos.py --apply-db --only-missing
  python sql/fetch_produit_photos.py --designation "Autoclave 18L"

Sur PythonAnywhere (avec DATABASE_URL / .env) :
  cd ~/AvalonPharmaInterne && python sql/fetch_produit_photos.py --apply-db --only-missing
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from PIL import Image
except ImportError:
    print("Pillow requis : pip install Pillow", file=sys.stderr)
    sys.exit(1)

USER_AGENT = "GestAvalon/1.0 (catalogue médical; contact: admin@avalonpharma.local)"
MIN_WIDTH = 200
MIN_HEIGHT = 160
REQUEST_DELAY = 0.35

CATEGORY_PATTERNS: list[tuple[str, str]] = [
    (r"^Aiguille", "biopsy needle medical"),
    (r"^Boîte|^Set |^Kit ", "surgical instrument set"),
    (r"^Gants", "sterile surgical gloves"),
    (r"^Pince|^Pinces", "surgical forceps"),
    (r"^Ciseaux", "surgical scissors"),
    (r"^Davier|^Écarteur", "surgical retractor forceps"),
    (r"^Papier ECG|^Rouleau papier ECG", "ECG paper roll"),
    (r"^Casaque|^Bonnet|^Couvre-chaussure", "surgical gown disposable medical"),
    (r"^Masque", "surgical mask box"),
    (r"^Bande de crêpe", "medical crepe bandage"),
    (r"^Valves d'Heimlich", "Heimlich valve chest drainage"),
    (r"^Table", "medical examination table"),
    (r"^Lampe à fente|Ophtalmoscope|Tonomètre|Lentille Volk|Échobiométrie|Autoréfracto", "ophthalmology equipment"),
    (r"^Microscope opératoire", "operating microscope"),
    (r"^Réfrigérateur médical", "medical refrigerator vaccine"),
    (r"^Imprimante Sony", "medical thermal printer"),
    (r"^Bistouri électrique", "electrosurgical unit"),
]

# Titres Wikipedia (anglais) pour vignette directe
WIKI_TITLES: dict[str, str] = {
    "Autoclave": "Autoclave",
    "Autoclave 18L": "Autoclave",
    "Nébuliseur": "Nebulizer",
    "Robinet 3 voies": "Stopcock",
    "Electrode Cardiaque p/50": "Electrocardiography",
    "Électrode B/50": "Electrocardiography",
    "Papier ECG 280x210 - 200 pages": "Electrocardiography",
    "Papier ECG 295x210 - 100 pages": "Electrocardiography",
    "Rouleau papier ECG 210mm x 20m": "Electrocardiography",
    "Gants Stériles T 7,5": "Surgical glove",
    "Gants Stériles T 8": "Surgical glove",
    "Gants stériles T 7,5": "Surgical glove",
    "Masque chirurgical B/50": "Surgical mask",
    "Surgicel": "Oxidized cellulose",
    "Valves d'Heimlich simple": "Heimlich valve",
    "Valves d'Heimlich double": "Heimlich valve",
    "Table Motorisée": "Operating table",
    "Table motorisée": "Operating table",
    "Table opératoire électrique": "Operating table",
    "Microscope opératoire": "Surgical microscope",
    "Lampe à fente": "Slit lamp",
    "Ophtalmoscope indirect": "Ophthalmoscopy",
    "Tonomètre": "Tonometer",
    "Réfrigérateur médical 400L": "Vaccine refrigerator",
    "Prolongateur 75 à 100 cm": "Peripheral venous catheter",
    "Filtre antibactérien": "Breathing circuit",
    "Filtre HME": "Heat and moisture exchanger",
    "Flacon de Redon 600 ml": "Surgical drain",
    "Pleurevac": "Chest tube",
    "Mandrin d'Eschmann": "Tracheal intubation",
    "Ciseaux Mayo courbes 14 cm": "Mayo scissors",
    "Ciseaux Metzenbaum courbes 14 cm": "Metzenbaum scissors",
    "Pince de Kelly courbe 10 cm": "Kelly forceps",
    "Implant": "Medical implant",
    "Robinet 3 voies": "Stopcock",
    "Valves d'Heimlich double": "Heimlich valve",
    "Lentille Volk 90": "Ophthalmology",
    "Échelle d'acuité + projecteur test": "Snellen chart",
    "Échobiométrie Scan AB": "Ophthalmology",
    "Papier échographie UPP-110-HG": "Medical ultrasound",
}

# Requêtes anglaises / médicales pour améliorer les résultats image
SEARCH_HINTS: dict[str, str] = {
    "Autoclave": "medical autoclave sterilizer",
    "Autoclave 18L": "medical autoclave 18 liter sterilizer",
    "Nébuliseur": "medical nebulizer inhaler",
    "Robinet 3 voies": "three-way stopcock medical IV",
    "Prolongateur 75 à 100 cm": "IV extension tube medical",
    "Gants Stériles T 7,5": "sterile surgical gloves",
    "Gants Stériles T 8": "sterile surgical gloves",
    "Gants stériles T 7,5": "sterile surgical gloves",
    "Gants de révision utérine": "gynecological examination gloves",
    "Gants pour invasion utérine": "obstetric gloves sterile",
    "Gants de soins B/100": "nitrile examination gloves box",
    "Masque chirurgical B/50": "surgical face mask box",
    "Electrode Cardiaque p/50": "ECG electrode pads",
    "Électrode B/50": "ECG electrode pads",
    "Papier ECG 280x210 - 200 pages": "ECG recording paper roll thermal",
    "Papier ECG 295x210 - 100 pages": "ECG recording paper thermal",
    "Rouleau papier ECG 210mm x 20m": "ECG paper roll thermal printer",
    "Papier échographie UPP-110-HG": "ultrasound printer paper roll",
    "Casaque renforcée XL stérile": "surgical gown reinforced sterile",
    "Casaque renforcée XXL stérile": "surgical gown reinforced sterile",
    "Davier articulaire": "bone holding clamp orthopedic",
    "Davier de Lambotte": "Lambotte bone clamp orthopedic",
    "Lentille Volk 90": "Volk 90D diagnostic lens",
    "Turbine à deux trous": "dental turbine handpiece",
    "Échelle d'acuité + projecteur test": "Snellen eye chart projector",
    "Échobiométrie Scan AB": "A-scan biometer ophthalmology ultrasound",
    "Écarteur Farabeuf 26x10": "Farabeuf retractor surgical",
    "Écarteur Farabeuf 30x10": "Farabeuf retractor surgical large",
    "Filtre antibactérien": "bacterial filter breathing circuit HME",
    "Filtre HME": "heat moisture exchanger filter tracheostomy",
    "Fil Antibactérienne": "antibacterial suture thread",
    "Valves d'Heimlich simple": "Heimlich valve chest drainage",
    "Valves d'Heimlich double": "Heimlich double valve chest drainage",
    "Surgicel": "Surgicel hemostatic gauze",
    "Trousse Universelle": "surgical instrument set tray",
    "Kit de traction adulte": "skeletal traction kit orthopedic",
    "Kit de traction enfant": "pediatric skeletal traction kit",
    "Réfrigérateur médical 400L": "medical refrigerator vaccine 400L",
    "Table Motorisée": "motorized medical examination table",
    "Table motorisée": "motorized medical examination table",
    "Table opératoire électrique": "electric operating table surgery",
    "Microscope opératoire": "operating microscope surgery",
    "Lampe à fente": "slit lamp ophthalmology",
    "Ophtalmoscope indirect": "indirect ophthalmoscope",
    "Tonomètre": "tonometer eye pressure",
    "Lentille Volk 90": "Volk 90D lens ophthalmology",
    "Capteur SPO2 doigt adulte + câble 2,5 m": "pulse oximeter finger sensor SpO2",
    "Brassard NIBP adulte 27-35 cm": "NIBP blood pressure cuff adult",
    "Flacon de Redon 600 ml": "Redon drainage bottle 600ml",
    "Pleurevac": "pleur-evac chest drainage system",
    "Implant": "orthopedic implant medical device",
    "Boîte d'amputation": "amputation surgical instrument set",
    "Boîte césarienne": "cesarean section instrument set",
    "Boîte d'accouchement": "delivery obstetric instrument set",
    "Set césarienne": "cesarean surgical set",
    "Set laparotomie": "laparotomy surgical instrument set",
    "Set de chirurgie générale": "general surgery instrument set",
    "Set orthopédie pédiatrique": "pediatric orthopedic instrument set",
    "Set vasculaire": "vascular surgery instrument set",
    "Set prostate": "prostate resection surgical set",
    "Set rénal": "renal surgery instrument set",
    "Set d'urologie": "urology surgical instrument set",
    "Set cataracte": "cataract surgery instrument set",
    "Kit pour cataracte": "cataract surgery kit ophthalmology",
    "Set amygdalectomie adulte": "tonsillectomy instrument set adult",
    "Set amygdalectomie pédiatrie": "tonsillectomy instrument set pediatric",
    "Ciseaux Mayo courbes 14 cm": "Mayo scissors curved surgical 14cm",
    "Ciseaux Metzenbaum courbes 14 cm": "Metzenbaum scissors curved",
    "Pince de Kelly courbe 10 cm": "Kelly forceps curved surgical",
    "Davier de Lambotte": "Lambotte bone holding forceps",
    "Davier articulaire": "bone holding forceps orthopedic",
    "Écarteur Farabeuf 10x6": "Farabeuf retractor surgical",
    "Écarteur Farabeuf 26x10": "Farabeuf retractor large surgical",
    "Écarteur Farabeuf 30x10": "Farabeuf retractor surgical",
    "Aiguille de biopsie 16G 200mm": "biopsy needle 16G coaxial",
    "Aiguille de bloc nerveux 22G - 100 mm": "nerve block needle 22G",
    "Aiguille de bloc nerveux 22G - 150 mm": "nerve block needle 22G 150mm",
    "Aiguille de bloc nerveux 22G - 80 mm": "nerve block needle 22G 80mm",
    "Clamp Barre": "Mayo-Hegar needle holder surgical",
    "Lame de delbet P/10": "Delbet surgical blade scalpel",
    "Mandrin d'Eschmann": "Eschmann introducer airway gum elastic bougie",
    "Guide sonde": "guidewire medical urology",
    "Bande de crêpe 10 cm": "crepe bandage medical 10cm",
    "Pièce de gaze (unité)": "medical gauze swab sterile",
    "Couvre-chaussure S/100": "shoe covers medical disposable",
    "Bonnet S/100": "surgical bouffant cap disposable",
    "Casaque renforcée XL stérile": "reinforced surgical gown sterile",
    "Casaque renforcée XXL stérile": "reinforced surgical gown sterile XXL",
    "Bistouri électrique Ysesu 350Y + accessoires": "electrosurgical unit diathermy",
    "Imprimante Sony": "Sony medical thermal printer UP-D",
    "Échobiométrie Scan AB": "A-scan ultrasound biometer ophthalmology",
}


def _slug(value: str, fallback: str = "produit") -> str:
    s = (value or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return (s[:48] or fallback)


def search_query(designation: str) -> str:
    if designation in SEARCH_HINTS:
        return SEARCH_HINTS[designation]
    for pattern, fallback in CATEGORY_PATTERNS:
        if re.search(pattern, designation, re.IGNORECASE):
            return fallback
    base = designation.strip()
    low = base.lower()
    if any(x in low for x in ("gant", "masque", "boîte", "set ", "kit ", "pince", "ciseau", "davier", "écarteur")):
        return f"{base} medical surgical"
    if "papier" in low or "ecg" in low:
        return f"{base} medical"
    return f"{base} medical equipment product"


def query_variants(designation: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    def add(q: str) -> None:
        q = (q or "").strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)

    add(search_query(designation))
    add(designation.strip())
    if designation in WIKI_TITLES:
        add(WIKI_TITLES[designation])
    words = designation.split()
    if len(words) > 3:
        add(" ".join(words[:3]) + " medical")
    if len(words) > 1:
        add(words[0] + " medical equipment")
    return out


def search_wikipedia_thumb(title: str) -> dict | None:
    from urllib.parse import quote

    safe = quote(title.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe}"
    try:
        data = http_get_json(url)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    thumb = (data.get("thumbnail") or {}).get("source")
    if not thumb or thumb.lower().endswith(".svg"):
        return None
    width = int((data.get("thumbnail") or {}).get("width") or 400)
    height = int((data.get("thumbnail") or {}).get("height") or 300)
    return {
        "url": thumb,
        "width": width,
        "height": height,
        "title": data.get("title") or title,
        "source": "wikipedia",
    }


def http_get_json(url: str, timeout: int = 20) -> Any:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def http_download(url: str, timeout: int = 25) -> bytes | None:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "image/jpeg,image/png,image/webp,*/*",
    }
    if "wikimedia.org" in url or "wikipedia.org" in url:
        headers["Referer"] = "https://commons.wikimedia.org/"
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if len(data) < 8000:
                return None
            if len(data) > 6 * 1024 * 1024:
                return None
            return data
    except (HTTPError, URLError, TimeoutError, ValueError):
        return None


def score_candidate(title: str, width: int, height: int, source: str, query: str) -> float:
    score = float(width * height)
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        score *= 0.15
    ratio = width / max(height, 1)
    if 0.6 <= ratio <= 1.8:
        score *= 1.15
    q_words = [w for w in re.split(r"\W+", query.lower()) if len(w) > 3]
    title_l = (title or "").lower()
    hits = sum(1 for w in q_words if w in title_l)
    score *= 1.0 + hits * 0.08
    if source == "wikimedia":
        score *= 1.2
    if source == "wikipedia":
        score *= 1.25
    return score


def search_wikimedia(query: str, limit: int = 8) -> list[dict]:
    params = urlencode(
        {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": 900,
        }
    )
    url = f"https://commons.wikimedia.org/w/api.php?{params}"
    try:
        data = http_get_json(url)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return []
    pages = (data.get("query") or {}).get("pages") or {}
    out = []
    for page in pages.values():
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        mime = (info.get("mime") or "").lower()
        if not mime.startswith("image/"):
            continue
        url_img = info.get("url") or info.get("thumburl")
        if not url_img:
            continue
        title = page.get("title") or ""
        out.append(
            {
                "url": url_img,
                "width": int(info.get("thumbwidth") or info.get("width") or 0),
                "height": int(info.get("thumbheight") or info.get("height") or 0),
                "title": title,
                "source": "wikimedia",
            }
        )
    return out


def search_openverse(query: str, limit: int = 10) -> list[dict]:
    params = urlencode({"q": query, "page_size": limit})
    url = f"https://api.openverse.org/v1/images/?{params}"
    try:
        data = http_get_json(url)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return []
    out = []
    for hit in data.get("results") or []:
        url_img = hit.get("url")
        if not url_img:
            continue
        out.append(
            {
                "url": url_img,
                "width": int(hit.get("width") or 0),
                "height": int(hit.get("height") or 0),
                "title": hit.get("title") or hit.get("id") or "",
                "source": "openverse",
            }
        )
    return out


def pick_best_image(designation: str) -> dict | None:
    candidates: list[dict] = []

    if designation in WIKI_TITLES:
        wiki = search_wikipedia_thumb(WIKI_TITLES[designation])
        if wiki:
            candidates.append(wiki)
        time.sleep(REQUEST_DELAY / 2)

    for query in query_variants(designation):
        for fn in (search_wikimedia, search_openverse):
            try:
                candidates.extend(fn(query, limit=6))
            except Exception:
                pass
            time.sleep(REQUEST_DELAY / 2)
        if candidates:
            break

    if not candidates:
        for pattern, fallback in CATEGORY_PATTERNS:
            if re.search(pattern, designation, re.IGNORECASE):
                try:
                    candidates.extend(search_openverse(fallback, limit=8))
                except Exception:
                    pass
                break

    if not candidates:
        return None
    seen_urls: set[str] = set()
    unique: list[dict] = []
    for c in candidates:
        u = c["url"]
        if not u or u.lower().endswith(".svg") or ".svg/" in u.lower():
            continue
        if u in seen_urls:
            continue
        seen_urls.add(u)
        unique.append(c)
    if not unique:
        return None
    query_ref = search_query(designation)
    unique.sort(
        key=lambda c: score_candidate(
            c.get("title", ""),
            c.get("width", 0),
            c.get("height", 0),
            c.get("source", ""),
            query_ref,
        ),
        reverse=True,
    )
    return unique[0]


def save_image_bytes(data: bytes, upload_root: Path, reference: str) -> tuple[str | None, str | None]:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        return None, "Image illisible"

    if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
        return None, f"Trop petite ({img.width}x{img.height})"

    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        alpha = img.split()[-1] if img.mode in ("RGBA", "LA") else None
        bg.paste(img, mask=alpha)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    produits_dir = upload_root / "produits"
    produits_dir.mkdir(parents=True, exist_ok=True)
    ref_slug = _slug(reference)
    filename = f"{ref_slug}_main_{uuid.uuid4().hex[:8]}.jpg"
    filepath = produits_dir / filename
    img.save(filepath, format="JPEG", quality=88, optimize=True)
    return f"produits/{filename}", None


def collect_seed_designations() -> list[str]:
    names: set[str] = set()
    seed_dir = ROOT / "sql"
    pat = re.compile(r'\("([^"]+)",\s*\d+,\s*\d+\)')
    for path in seed_dir.glob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in pat.finditer(text):
            names.add(m.group(1))
    return sorted(names)


def load_produits_from_db(only_missing: bool, designation_filter: str | None):
    from app import create_app
    from app.models.produit import Produit

    app = create_app()
    with app.app_context():
        q = Produit.query.filter_by(est_actif=True).order_by(Produit.designation)
        if only_missing:
            q = q.filter((Produit.photo_principale.is_(None)) | (Produit.photo_principale == ""))
        if designation_filter:
            q = q.filter(Produit.designation.ilike(f"%{designation_filter}%"))
        return [(p.id, p.reference, p.designation, p.photo_principale) for p in q.all()]


def apply_photo_to_db(produit_id: int | None, designation: str, stored_path: str, dry_run: bool) -> bool:
    if dry_run:
        return False
    from app import create_app
    from app.extensions import db
    from app.models.produit import Produit

    app = create_app()
    with app.app_context():
        p = None
        if produit_id:
            p = Produit.query.get(produit_id)
        if not p and designation:
            p = Produit.query.filter_by(designation=designation).first()
        if not p:
            return False
        p.photo_principale = stored_path
        db.session.commit()
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Télécharge des photos produit depuis le web (sources libres).")
    parser.add_argument("--dry-run", action="store_true", help="Recherche sans télécharger ni écrire en base")
    parser.add_argument("--apply-db", action="store_true", help="Met à jour photo_principale en base")
    parser.add_argument("--only-missing", action="store_true", help="Uniquement les produits sans photo")
    parser.add_argument("--from-seed", action="store_true", help="Utilise les désignations des scripts seed (sans DB)")
    parser.add_argument("--designation", type=str, help="Filtrer une désignation")
    parser.add_argument("--limit", type=int, default=0, help="Limiter le nombre de produits")
    parser.add_argument("--skip-cached", action="store_true", help="Ignore les produits déjà dans le manifeste OK")
    parser.add_argument("--retry-failed", action="store_true", help="Retente uniquement les échecs du manifeste")
    args = parser.parse_args()

    upload_root = ROOT / "instance" / "uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / "instance" / "produit_photos_manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}

    items: list[tuple] = []
    if args.from_seed or not args.apply_db:
        designations = collect_seed_designations()
        if args.designation:
            designations = [d for d in designations if args.designation.lower() in d.lower()]
        items = [(None, _slug(d, "prd"), d, None) for d in designations]
    if args.apply_db:
        try:
            db_items = load_produits_from_db(args.only_missing, args.designation)
            if db_items:
                items = db_items
        except Exception as exc:
            print(f"⚠ Base indisponible ({exc}) — repli sur les seeds.", file=sys.stderr)
            if not items:
                items = [
                    (None, _slug(d, "prd"), d, None)
                    for d in collect_seed_designations()
                ]

    if args.retry_failed and manifest:
        failed_names = [k for k, v in manifest.items() if not v.get("ok")]
        items = [(None, _slug(d, "prd"), d, None) for d in failed_names]
        if args.designation:
            items = [it for it in items if args.designation.lower() in it[2].lower()]

    if args.limit and args.limit > 0:
        items = items[: args.limit]

    if not items:
        print("Aucun produit à traiter.")
        return 0

    ok = skip = fail = 0
    print(f"Traitement de {len(items)} produit(s)…\n")

    for produit_id, reference, designation, existing in items:
        ref = reference or _slug(designation)
        print(f"• {designation}")
        if existing and args.only_missing:
            print("  ↷ photo déjà présente\n")
            skip += 1
            continue
        if args.skip_cached and manifest.get(designation, {}).get("ok"):
            print("  ↷ déjà téléchargé (manifeste)\n")
            skip += 1
            continue

        if args.dry_run:
            best = pick_best_image(designation)
            if best:
                print(f"  ✓ candidat [{best['source']}] {best.get('width')}x{best.get('height')} — {best['url'][:90]}…\n")
                ok += 1
            else:
                print("  ✗ aucune image trouvée\n")
                fail += 1
            continue

        best = pick_best_image(designation)
        if not best:
            print("  ✗ aucune image trouvée\n")
            fail += 1
            manifest[designation] = {"ok": False, "error": "not_found"}
            continue

        data = http_download(best["url"])
        if not data:
            print(f"  ✗ téléchargement échoué\n")
            fail += 1
            manifest[designation] = {"ok": False, "error": "download_failed", "url": best["url"]}
            continue

        stored, err = save_image_bytes(data, upload_root, ref)
        if not stored:
            print(f"  ✗ {err}\n")
            fail += 1
            manifest[designation] = {"ok": False, "error": err, "url": best["url"]}
            continue

        if args.apply_db:
            linked = apply_photo_to_db(produit_id, designation, stored, dry_run=False)
            if not linked and produit_id is None:
                print("  ⚠ photo locale enregistrée (produit non trouvé en base)\n")

        manifest[designation] = {
            "ok": True,
            "stored": stored,
            "source": best["source"],
            "url": best["url"],
            "title": best.get("title"),
        }
        print(f"  ✓ {stored} [{best['source']}]\n")
        ok += 1
        time.sleep(REQUEST_DELAY)

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Terminé : {ok} OK, {skip} ignorés, {fail} échecs.")
    print(f"Manifeste : {manifest_path}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
