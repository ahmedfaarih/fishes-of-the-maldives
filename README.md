# Masveriyaa Fish API

Searchable REST API for 370 fish species of the Maldives, extracted from *Fishes of the Maldives* (Marine Research Centre, 2003).

## Setup

```bash
pip install -r requirements.txt
python extract_from_pdf.py /path/to/fishes-of-the-maldives.pdf   # run once
python api.py
```

API runs at `http://localhost:8000` — interactive docs at `http://localhost:8000/docs`

## Endpoints

### General

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/fish` | List and filter fish |
| GET | `/api/fish/{id}` | Get fish by ID |
| GET | `/api/fish/slug/{slug}` | Get fish by slug |
| GET | `/api/search` | Full-text search (all fields) |
| GET | `/api/families` | All families with species counts |
| GET | `/api/stats` | Summary statistics |
| GET | `/images/drawings/{file}` | Line drawing images |
| GET | `/images/photos/{file}` | Color plate photos |

### English (`/api/en`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/en/search` | Search, English-format response |
| GET | `/api/en/fish/{id}` | Get fish by ID, English-format response |

### Dhivehi (`/api/dh`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dh/search` | Search in Dhivehi — accepts Thaana script or Latin romanization |
| GET | `/api/dh/fish/{id}` | Get fish by ID, Dhivehi-format response |

The Dhivehi search endpoint automatically detects Thaana input and converts it to Latin before matching against the stored romanized local names. Both `ↄིЯRu` and `miyaru` will return the same results.

### Query Parameters

**`/api/fish`**

| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Search text |
| `family` | string | Filter by family (e.g. `SCOMBRIDAE`) |
| `order` | string | Filter by order |
| `has_photo` | bool | Filter to species with color photos |
| `page` | int | Page number (default: 1) |
| `limit` | int | Results per page (default: 20, max: 100) |

**`/api/search`, `/api/en/search`, `/api/dh/search`**

| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Search query (required) |
| `limit` | int | Max results (default: 10, max: 50) |

## Response Format

### English (`/api/en`)

```json
{
  "id": 3,
  "slug": "whale-shark",
  "english_name": "Whale Shark",
  "local_name": "Fehurihi",
  "scientific_name": "Rhincodon typus",
  "family": "RHINCODONTIDAE",
  "order": "Orectolobiformes",
  "max_size": "Rare above 12 m; possible to 21 m",
  "distinctive_characters": "...",
  "colour": "...",
  "habitat": "...",
  "distribution": "Circumtropical.",
  "image_url": "/images/drawings/drawing_20.png",
  "drawing_url": "/images/drawings/drawing_20.png",
  "photo_url": null
}
```

### Dhivehi (`/api/dh`)

```json
{
  "id": 3,
  "local_name": "Fehurihi",
  "local_name_latin": "Fehurihi",
  "scientific_name": "Rhincodon typus",
  "english_name": "Whale Shark",
  "family": "RHINCODONTIDAE",
  "max_size": "Rare above 12 m; possible to 21 m",
  "distinctive_characters": "...",
  "colour": "...",
  "habitat": "...",
  "distribution": "Circumtropical.",
  "image_url": "/images/drawings/drawing_20.png",
  "drawing_url": "/images/drawings/drawing_20.png",
  "photo_url": null
}
```

`local_name` returns Thaana script (`local_name_dv`) when available, otherwise falls back to the Latin romanization. `local_name_latin` always contains the Latin romanization.

Search responses include a `query_latin` field when Thaana input was detected, showing what the query was converted to before matching.

## Project Structure

```
masveriyaa-api/
├── api.py
├── extract_from_pdf.py
├── requirements.txt
├── data/
│   ├── fishes.json          # Full species database (370 species)
│   ├── fishes_summary.json  # Lightweight index
│   └── families.json
└── images/
    ├── drawings/            # B&W line drawings (~370 files)
    └── photos/              # Color plate thumbnails (~48 files)
```

## Notes

- Line drawings are inverted (white on black). Invert them in the client for a light-background UI.
- Color photos are small thumbnails extracted from the book's plate pages.
- Local names are stored as Latin romanizations of Dhivehi. Thaana script (`local_name_dv`) is not yet populated for most species.
- Source data is from 2003 — some taxonomy may have changed since publication.

