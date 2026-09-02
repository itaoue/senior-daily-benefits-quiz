#!/usr/bin/env python3
"""
Put a real, licensed photo of a public figure on an article, from Wikimedia
Commons, with the attribution line the license requires.

    python tools/fetch_person_photo.py --slug <article-slug> --query "Warren Buffett" [--pick 0] [--anchor 0.15]
    python tools/fetch_person_photo.py --slug <article-slug> --title "File:Exact Name.jpg" [--anchor 0.15]
    python tools/fetch_person_photo.py --query "Mark Cuban" --list        # just show candidates
    add --fit for a portrait-orientation photo (whole image, navy pillarbox)

Only public-domain, CC0, CC BY and CC BY-SA files are accepted. The image is
resized to 1200 wide and cropped to 630 tall; --anchor is the vertical focal
point (0 = keep the top, 0.5 = center). Writes src/static/images/articles/<slug>.jpg
and sets `image:` and `image_credit:` in the article's front matter.
Standard library only; cropping uses macOS sips.
"""
import argparse, json, pathlib, re, shutil, subprocess, sys, urllib.parse, urllib.request, html as htmlmod

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "articles"
OUT = ROOT / "src" / "static" / "images" / "articles"
UA = {"User-Agent": "SeniorDailyBenefits/1.0 (https://seniordailybenefits.com; itaoue@gmail.com)"}
OK = ("Public domain", "CC0", "CC BY 2.0", "CC BY 2.5", "CC BY 3.0", "CC BY 4.0",
      "CC BY-SA 2.0", "CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0")


def api(params):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({**params, "format": "json"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def candidates(query, limit=20):
    d = api({"action": "query", "generator": "search", "gsrsearch": query + " filetype:bitmap",
             "gsrnamespace": 6, "gsrlimit": limit, "prop": "imageinfo",
             "iiprop": "url|extmetadata|size", "iiurlwidth": 2000})
    rows = []
    for p in d.get("query", {}).get("pages", {}).values():
        ii = p["imageinfo"][0]
        lic = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "?")
        if lic in OK and ii["width"] >= 1000:
            rows.append((p["title"], lic, ii["width"], ii["height"], ii))
    rows.sort(key=lambda r: r[2] * r[3], reverse=True)
    return rows


def by_title(title):
    d = api({"action": "query", "titles": title, "prop": "imageinfo",
             "iiprop": "url|extmetadata|size", "iiurlwidth": 2000})
    p = list(d["query"]["pages"].values())[0]
    if "imageinfo" not in p:
        sys.exit(f"not found on Commons: {title}")
    ii = p["imageinfo"][0]
    lic = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "?")
    if lic not in OK:
        sys.exit(f"license not accepted: {lic}")
    return (p["title"], lic, ii["width"], ii["height"], ii)


def strip_tags(s):
    return htmlmod.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def credit_line(title, lic, ii):
    md = ii.get("extmetadata", {})
    artist = strip_tags(md.get("Artist", {}).get("value", ""))
    artist = re.sub(r"\s+", " ", artist)[:60] or "Wikimedia Commons"
    if lic == "Public domain":
        return f"Photo: {artist} / Wikimedia Commons, public domain"
    return f"Photo: {artist} / Wikimedia Commons, {lic}"


def download_and_crop(ii, target, anchor, fit=False):
    url = ii.get("thumburl") or ii["url"]
    data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
    target.write_bytes(data)
    if not shutil.which("sips"):
        print("  (sips not found; image left uncropped)"); return
    if fit:  # portrait: show the whole subject, pillarbox with brand navy
        subprocess.run(["sips", "--resampleHeight", "630", str(target)], check=True, capture_output=True)
        subprocess.run(["sips", "--padToHeightWidth", "630", "1200", "--padColor", "1B2E5A", str(target)],
                       check=True, capture_output=True)
        return
    subprocess.run(["sips", "--resampleWidth", "1200", str(target)], check=True, capture_output=True)
    h = int(subprocess.run(["sips", "-g", "pixelHeight", str(target)], capture_output=True, text=True).stdout.split()[-1])
    if h < 630:  # too wide: resize by height then center-crop width
        subprocess.run(["sips", "--resampleHeight", "630", str(target)], check=True, capture_output=True)
        subprocess.run(["sips", "-c", "630", "1200", str(target)], check=True, capture_output=True)
        return
    offset = int(max(0, min(h - 630, (h - 630) * anchor * 2)))  # anchor 0.5 == centered
    subprocess.run(["sips", "-c", "630", "1200", "--cropOffset", str(offset), "0", str(target)],
                   check=True, capture_output=True)


def set_fields(path, rel, credit):
    text = path.read_text()
    text = re.sub(r"^image_credit:.*\n", "", text, count=1, flags=re.M)
    if re.search(r"^image:", text, re.M):
        text = re.sub(r"^image:.*$", f"image: {rel}\nimage_credit: {credit}", text, count=1, flags=re.M)
    else:
        text = re.sub(r"^(summary:.*)$", rf"\1\nimage: {rel}\nimage_credit: {credit}", text, count=1, flags=re.M)
    path.write_text(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    ap.add_argument("--query")
    ap.add_argument("--title")
    ap.add_argument("--pick", type=int, default=0)
    ap.add_argument("--anchor", type=float, default=0.15, help="0 top .. 0.5 center")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--fit", action="store_true", help="portrait photo: fit whole image, pillarbox in navy")
    a = ap.parse_args()

    if a.title:
        chosen = by_title(a.title)
    elif a.query:
        rows = candidates(a.query)
        if a.list or not a.slug:
            for i, (t, lic, w, h, _) in enumerate(rows):
                print(f"[{i}] {lic:14s} {w}x{h} {'L' if w > h else 'P'} {t}")
            return
        if not rows:
            sys.exit("no acceptable candidates")
        chosen = rows[a.pick]
    else:
        sys.exit("give --query or --title")

    title, lic, w, h, ii = chosen
    art = next((p for p in CONTENT.glob("*.md") if re.search(rf"^slug:\s*{re.escape(a.slug)}\s*$", p.read_text(), re.M)), None)
    if not art:
        sys.exit(f"no article with slug {a.slug}")
    OUT.mkdir(parents=True, exist_ok=True)
    rel = f"images/articles/{a.slug}.jpg"
    target = ROOT / "src" / "static" / rel
    download_and_crop(ii, target, a.anchor, a.fit)
    credit = credit_line(title, lic, ii)
    set_fields(art, rel, credit)
    print(f"{a.slug}\n  {title} ({lic}, {w}x{h})\n  -> {rel}\n  credit: {credit}")


if __name__ == "__main__":
    main()
