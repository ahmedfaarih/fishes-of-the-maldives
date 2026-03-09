"""
Extract fish species data and images from 'Fishes of the Maldives' PDF.
Run this once to generate the JSON database and image files.

Usage:
    python extract_from_pdf.py /path/to/fishes-of-the-maldives.pdf
"""

import fitz  # pymupdf
import re
import json
import os
import sys
from pathlib import Path


def parse_species_page(page, page_num):
    """Parse a single species page and return structured data."""
    text = page.get_text()

    if "English Name" not in text and "Local Name" not in text:
        return None

    lines = text.strip().split("\n")

    # Scientific name: line after page number
    scientific = ""
    for idx, line in enumerate(lines):
        if re.match(r"^\d+$", line.strip()):
            if idx + 1 < len(lines):
                sci_line = lines[idx + 1].strip()
                sci_line = re.sub(r"\s+\(?\w+,?\s*\d{4}\)?.*$", "", sci_line).strip()
                scientific = sci_line
            break

    # Structured fields
    def extract(pattern):
        m = re.search(pattern, text)
        return m.group(1).strip() if m else ""

    english = extract(r"English Name\s*:\s*(.+)")
    local = extract(r"Local Name\s*:\s*(.+)")
    family = extract(r"Family\s*:\s*([A-Z]+)")
    order = extract(r"Order\s*:\s*(.+)")
    size = extract(r"Size\s*:\s*(.+)")

    # Description sections
    def extract_section(start, stops):
        stop_pattern = "|".join(stops)
        pattern = rf"{start}:\s*(.+?)(?={stop_pattern}|$)"
        m = re.search(pattern, text, re.DOTALL)
        return " ".join(m.group(1).split()) if m else ""

    stops = ["Colour:", "Habitat", "Distribution", "Remarks"]

    species = {
        "page": page_num,
        "scientific_name": scientific,
        "english_name": english,
        "local_name": local,
        "family": family,
        "order": order,
        "max_size": size,
        "distinctive_characters": extract_section("Distinctive Characters", stops),
        "colour": extract_section("Colour", ["Habitat", "Distribution", "Remarks"]),
        "habitat": extract_section("Habitat and Biology", ["Distribution", "Remarks"]),
        "distribution": extract_section("Distribution", ["Remarks"]),
        "remarks": extract_section("Remarks", []),
    }

    if not local and not english:
        return None

    return species


def extract_line_drawing(doc, page_num, output_dir):
    """Extract the main line drawing from a species page."""
    page = doc[page_num]
    images = page.get_images()

    if not images:
        return None

    # Image [0] is the fish line drawing; [1] is the full-page text scan.
    # Always pick the first image.
    first_img = images[0]
    xref = first_img[0]
    try:
        base = doc.extract_image(xref)
    except Exception:
        return None
    ext = base["ext"]
    filename = f"drawing_{page_num}.{ext}"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "wb") as f:
        f.write(base["image"])

    return filename


def extract_color_plates(doc, output_dir):
    """Extract color photographs from the plate pages (410-415)."""
    plate_map = {}  # scientific_name -> photo filename

    for page_num in range(410, 416):
        page = doc[page_num]
        text = page.get_text()
        images = page.get_images()

        # Parse labels like "a. Carcharhinus amblyrhynchos"
        labels = re.findall(r"[a-h]\.\s*(.+)", text)

        # Extract images (skip very small ones like dividers)
        photo_images = []
        for img in images:
            xref = img[0]
            try:
                base = doc.extract_image(xref)
                if base["width"] > 80 and base["height"] > 80:
                    photo_images.append((xref, base))
            except Exception:
                continue

        # Match labels to images (they correspond in order)
        for idx, (xref, base) in enumerate(photo_images):
            ext = base["ext"]
            filename = f"photo_plate{page_num - 409}_{idx}.{ext}"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(base["image"])

            if idx < len(labels):
                plate_map[labels[idx].strip()] = filename

    return plate_map


def main(pdf_path):
    output_base = Path(__file__).parent
    drawings_dir = output_base / "images" / "drawings"
    photos_dir = output_base / "images" / "photos"
    data_dir = output_base / "data"

    for d in [drawings_dir, photos_dir, data_dir]:
        d.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    print(f"Opened PDF: {doc.page_count} pages")

    # --- Step 1: Parse all species ---
    print("\n[1/3] Parsing species data...")
    species_list = []
    for i in range(18, 410):
        species = parse_species_page(doc[i], i)
        if species:
            species["id"] = len(species_list) + 1
            species_list.append(species)

    print(f"  Found {len(species_list)} species")

    # --- Step 2: Extract line drawings ---
    print("\n[2/3] Extracting line drawings...")
    drawing_count = 0
    for species in species_list:
        filename = extract_line_drawing(doc, species["page"], str(drawings_dir))
        species["drawing"] = filename
        if filename:
            drawing_count += 1

    print(f"  Extracted {drawing_count} drawings")

    # --- Step 3: Extract color plates ---
    print("\n[3/3] Extracting color plates...")
    plate_map = extract_color_plates(doc, str(photos_dir))
    print(f"  Extracted {len(plate_map)} plate photos")

    # Match plates to species by scientific name
    photo_count = 0
    for species in species_list:
        sci = species["scientific_name"]
        if sci in plate_map:
            species["photo"] = plate_map[sci]
            photo_count += 1
        else:
            species["photo"] = None

    print(f"  Matched {photo_count} photos to species")

    # --- Step 4: Generate slug/ID for URL-friendly access ---
    for species in species_list:
        slug = species["english_name"].lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
        species["slug"] = slug

    # --- Save JSON ---
    output_file = data_dir / "fishes.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(species_list, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Saved to {output_file}")
    print(f"  {len(species_list)} species")
    print(f"  {drawing_count} line drawings in {drawings_dir}")
    print(f"  {len(plate_map)} color photos in {photos_dir}")

    # Also generate a smaller summary file for quick lookups
    summary = []
    for s in species_list:
        summary.append({
            "id": s["id"],
            "slug": s["slug"],
            "scientific_name": s["scientific_name"],
            "english_name": s["english_name"],
            "local_name": s["local_name"],
            "family": s["family"],
            "max_size": s["max_size"],
            "has_photo": s["photo"] is not None,
            "has_drawing": s["drawing"] is not None,
        })

    summary_file = data_dir / "fishes_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"  Summary index saved to {summary_file}")

    # Generate family index
    families = {}
    for s in species_list:
        fam = s["family"]
        if fam not in families:
            families[fam] = {"family": fam, "count": 0, "species": []}
        families[fam]["count"] += 1
        families[fam]["species"].append(s["id"])

    families_file = data_dir / "families.json"
    with open(families_file, "w", encoding="utf-8") as f:
        json.dump(list(families.values()), f, indent=2, ensure_ascii=False)

    print(f"  {len(families)} families indexed to {families_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_from_pdf.py <path-to-pdf>")
        sys.exit(1)
    main(sys.argv[1])
