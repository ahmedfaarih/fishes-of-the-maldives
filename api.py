import json
import re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


# Thaana consonants → Latin romanization.
# alifu (U+0787) is a silent vowel carrier; ainu (U+07A2) is silent in Dhivehi.
_THAANA_CONSONANTS = {
    '\u0780': 'h',    # ހ
    '\u0781': 'sh',   # ށ
    '\u0782': 'n',    # ނ
    '\u0783': 'r',    # ރ
    '\u0784': 'b',    # ބ
    '\u0785': 'lh',   # ޅ
    '\u0786': 'k',    # ކ
    '\u0787': '',     # އ alifu
    '\u0788': 'v',    # ވ
    '\u0789': 'm',    # މ
    '\u078A': 'f',    # ފ
    '\u078B': 'dh',   # ދ
    '\u078C': 'th',   # ތ
    '\u078D': 'l',    # ލ
    '\u078E': 'g',    # ގ
    '\u078F': 'ny',   # ޏ
    '\u0790': 's',    # ސ
    '\u0791': 'd',    # ޑ
    '\u0792': 'z',    # ޒ
    '\u0793': 't',    # ޓ
    '\u0794': 'y',    # ޔ
    '\u0795': 'p',    # ޕ
    '\u0796': 'j',    # ޖ
    '\u0797': 'ch',   # ޗ
    # Arabic loanword letters
    '\u0798': 'tt',   # ޘ
    '\u0799': 'hh',   # ޙ
    '\u079A': 'kh',   # ޚ
    '\u079B': 'th',   # ޛ
    '\u079C': 'z',    # ޜ
    '\u079D': 'sh',   # ޝ
    '\u079E': 's',    # ޞ
    '\u079F': 'dh',   # ޟ
    '\u07A0': 't',    # ޠ
    '\u07A1': 'z',    # ޡ
    '\u07A2': '',     # ޢ ainu (silent)
    '\u07A3': 'gh',   # ޣ
    '\u07A4': 'q',    # ޤ
    '\u07A5': 'w',    # ޥ
}

# Vowel diacritics. Sukun (U+07B0) marks a consonant cluster with no following vowel.
_THAANA_VOWELS = {
    '\u07A6': 'a',
    '\u07A7': 'aa',
    '\u07A8': 'i',
    '\u07A9': 'ee',
    '\u07AA': 'u',
    '\u07AB': 'oo',
    '\u07AC': 'e',
    '\u07AD': 'ey',
    '\u07AE': 'o',
    '\u07AF': 'oa',
    '\u07B0': '',     # sukun — no vowel
}

_THAANA_RANGE = re.compile(r'[\u0780-\u07BF]')


def is_thaana(text: str) -> bool:
    return bool(_THAANA_RANGE.search(text))


def thaana_to_latin(text: str) -> str:
    result = []
    for ch in text:
        if ch in _THAANA_CONSONANTS:
            result.append(_THAANA_CONSONANTS[ch])
        elif ch in _THAANA_VOWELS:
            result.append(_THAANA_VOWELS[ch])
        else:
            result.append(ch)
    return ''.join(result)


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

with open(DATA_DIR / "fishes.json", "r", encoding="utf-8") as f:
    ALL_FISH = json.load(f)

with open(DATA_DIR / "families.json", "r", encoding="utf-8") as f:
    ALL_FAMILIES = json.load(f)

FISH_BY_ID = {fish["id"]: fish for fish in ALL_FISH}
FISH_BY_SLUG = {fish["slug"]: fish for fish in ALL_FISH}

SEARCH_INDEX = {}
for fish in ALL_FISH:
    searchable = " ".join([
        fish.get("scientific_name", ""),
        fish.get("english_name", ""),
        fish.get("local_name", ""),
        fish.get("family", ""),
        fish.get("order", ""),
        fish.get("colour", ""),
        fish.get("habitat", ""),
        fish.get("distinctive_characters", ""),
        fish.get("remarks", ""),
    ]).lower()
    SEARCH_INDEX[fish["id"]] = searchable

SEARCH_INDEX_DV = {}
for fish in ALL_FISH:
    searchable_dv = " ".join([
        fish.get("local_name_dv", ""),
        fish.get("local_name", ""),
        fish.get("scientific_name", ""),
        fish.get("english_name", ""),
        fish.get("family", ""),
    ])
    SEARCH_INDEX_DV[fish["id"]] = searchable_dv


app = FastAPI(
    title="Masveriyaa Fish API",
    description="Searchable API for 370 fish species of the Maldives",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/images/drawings", StaticFiles(directory=str(BASE_DIR / "images" / "drawings")), name="drawings")
app.mount("/images/photos", StaticFiles(directory=str(BASE_DIR / "images" / "photos")), name="photos")


def fish_response(fish: dict, base_url: str = "") -> dict:
    result = {**fish}
    if fish.get("drawing"):
        result["drawing_url"] = f"/images/drawings/{fish['drawing']}"
    if fish.get("photo"):
        result["photo_url"] = f"/images/photos/{fish['photo']}"
    return result


def _best_image_url(fish: dict) -> Optional[str]:
    if fish.get("photo"):
        return f"/images/photos/{fish['photo']}"
    if fish.get("drawing"):
        return f"/images/drawings/{fish['drawing']}"
    return None


def en_response(fish: dict) -> dict:
    return {
        "id": fish["id"],
        "slug": fish["slug"],
        "english_name": fish["english_name"],
        "local_name": fish["local_name"],
        "scientific_name": fish["scientific_name"],
        "family": fish["family"],
        "order": fish.get("order", ""),
        "max_size": fish.get("max_size", ""),
        "distinctive_characters": fish.get("distinctive_characters", ""),
        "colour": fish.get("colour", ""),
        "habitat": fish.get("habitat", ""),
        "distribution": fish.get("distribution", ""),
        "image_url": _best_image_url(fish),
        "drawing_url": f"/images/drawings/{fish['drawing']}" if fish.get("drawing") else None,
        "photo_url": f"/images/photos/{fish['photo']}" if fish.get("photo") else None,
    }


def dh_response(fish: dict) -> dict:
    return {
        "id": fish["id"],
        "local_name": fish.get("local_name_dv") or fish["local_name"],
        "local_name_latin": fish["local_name"],
        "scientific_name": fish["scientific_name"],
        "english_name": fish["english_name"],
        "family": fish["family"],
        "max_size": fish.get("max_size", ""),
        "distinctive_characters": fish.get("distinctive_characters", ""),
        "colour": fish.get("colour", ""),
        "habitat": fish.get("habitat", ""),
        "distribution": fish.get("distribution", ""),
        "image_url": _best_image_url(fish),
        "drawing_url": f"/images/drawings/{fish['drawing']}" if fish.get("drawing") else None,
        "photo_url": f"/images/photos/{fish['photo']}" if fish.get("photo") else None,
    }


@app.get("/api/fish")
def list_fish(
    q: Optional[str] = Query(None, description="Search query (name, family, etc.)"),
    family: Optional[str] = Query(None, description="Filter by family name"),
    order: Optional[str] = Query(None, description="Filter by order"),
    has_photo: Optional[bool] = Query(None, description="Filter by has color photo"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    results = ALL_FISH

    if q:
        q_lower = q.lower()
        matching_ids = {fid for fid, text in SEARCH_INDEX.items() if q_lower in text}
        results = [f for f in results if f["id"] in matching_ids]

    if family:
        results = [f for f in results if f["family"] == family.upper()]

    if order:
        results = [f for f in results if f.get("order", "").lower() == order.lower()]

    if has_photo is not None:
        results = [f for f in results if (f.get("photo") is not None) == has_photo]

    total = len(results)
    start = (page - 1) * limit
    paginated = results[start:start + limit]

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
        "data": [fish_response(f) for f in paginated],
    }


@app.get("/api/fish/{fish_id}")
def get_fish(fish_id: int):
    fish = FISH_BY_ID.get(fish_id)
    if not fish:
        raise HTTPException(status_code=404, detail="Fish not found")
    return fish_response(fish)


@app.get("/api/fish/slug/{slug}")
def get_fish_by_slug(slug: str):
    fish = FISH_BY_SLUG.get(slug)
    if not fish:
        raise HTTPException(status_code=404, detail="Fish not found")
    return fish_response(fish)


@app.get("/api/search")
def search_fish(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
):
    q_lower = q.lower()
    results = []

    for fish in ALL_FISH:
        if q_lower not in SEARCH_INDEX[fish["id"]]:
            continue

        score = 1
        if q_lower in fish.get("english_name", "").lower():
            score += 10
        if q_lower in fish.get("local_name", "").lower():
            score += 10
        if q_lower in fish.get("scientific_name", "").lower():
            score += 5
        if q_lower in fish.get("family", "").lower():
            score += 3

        results.append({
            "id": fish["id"],
            "slug": fish["slug"],
            "scientific_name": fish["scientific_name"],
            "english_name": fish["english_name"],
            "local_name": fish["local_name"],
            "family": fish["family"],
            "drawing_url": f"/images/drawings/{fish['drawing']}" if fish.get("drawing") else None,
            "photo_url": f"/images/photos/{fish['photo']}" if fish.get("photo") else None,
            "score": score,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return {"query": q, "total": len(results), "data": results[:limit]}


@app.get("/api/families")
def list_families():
    return {"total": len(ALL_FAMILIES), "data": ALL_FAMILIES}


@app.get("/api/stats")
def get_stats():
    photos = sum(1 for f in ALL_FISH if f.get("photo"))
    drawings = sum(1 for f in ALL_FISH if f.get("drawing"))
    families = len(set(f["family"] for f in ALL_FISH if f.get("family")))
    orders = len(set(f.get("order", "") for f in ALL_FISH if f.get("order")))

    return {
        "total_species": len(ALL_FISH),
        "with_color_photo": photos,
        "with_drawing": drawings,
        "families": families,
        "orders": orders,
    }


@app.get("/api/en/search")
def en_search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
):
    q_lower = q.lower()
    results = []

    for fish in ALL_FISH:
        if q_lower not in SEARCH_INDEX[fish["id"]]:
            continue

        score = 1
        if q_lower in fish.get("local_name", "").lower():
            score += 10
        if q_lower in fish.get("english_name", "").lower():
            score += 10
        if q_lower in fish.get("scientific_name", "").lower():
            score += 5
        if q_lower in fish.get("family", "").lower():
            score += 3

        results.append({
            "id": fish["id"],
            "slug": fish["slug"],
            "english_name": fish["english_name"],
            "local_name": fish["local_name"],
            "scientific_name": fish["scientific_name"],
            "family": fish["family"],
            "image_url": _best_image_url(fish),
            "score": score,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    for r in results:
        del r["score"]
    return {"query": q, "lang": "en", "total": len(results), "data": results[:limit]}


@app.get("/api/en/fish/{fish_id}")
def en_get_fish(fish_id: int):
    fish = FISH_BY_ID.get(fish_id)
    if not fish:
        raise HTTPException(status_code=404, detail="Fish not found")
    return en_response(fish)


@app.get("/api/dh/search")
def dh_search(
    q: str = Query(..., min_length=1, description="Search query (Thaana script or Latin romanization)"),
    limit: int = Query(10, ge=1, le=50),
):
    """Accepts Thaana script or Latin romanization. Thaana input is automatically
    converted to Latin before matching against the stored romanized local names."""
    results = []

    q_latin = thaana_to_latin(q).lower() if is_thaana(q) else q.lower()

    for fish in ALL_FISH:
        search_text = SEARCH_INDEX_DV[fish["id"]]
        local_latin = fish.get("local_name", "").lower()
        local_dv = fish.get("local_name_dv", "")

        matched = (
            q_latin in local_latin
            or q_latin in search_text.lower()
            or (local_dv and q in local_dv)
        )
        if not matched:
            continue

        score = 1
        if q_latin in local_latin:
            score += 15
        if local_dv and q in local_dv:
            score += 15
        if q_latin in fish.get("english_name", "").lower():
            score += 5
        if q_latin in fish.get("scientific_name", "").lower():
            score += 3

        results.append({
            "id": fish["id"],
            "local_name": fish.get("local_name_dv") or fish["local_name"],
            "local_name_latin": fish["local_name"],
            "scientific_name": fish["scientific_name"],
            "english_name": fish["english_name"],
            "family": fish["family"],
            "image_url": _best_image_url(fish),
            "score": score,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    for r in results:
        del r["score"]
    return {
        "query": q,
        "query_latin": q_latin if is_thaana(q) else None,
        "lang": "dh",
        "total": len(results),
        "data": results[:limit],
    }


@app.get("/api/dh/fish/{fish_id}")
def dh_get_fish(fish_id: int):
    fish = FISH_BY_ID.get(fish_id)
    if not fish:
        raise HTTPException(status_code=404, detail="Fish not found")
    return dh_response(fish)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
