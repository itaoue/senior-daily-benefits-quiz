#!/usr/bin/env python3
"""
Generate a photorealistic hero image for each article with the xAI image API
and record it in the article's front matter (`image: images/articles/<slug>.jpg`).

    export XAI_API_KEY=xai-...
    python tools/make_article_art.py                 # every article without an image
    python tools/make_article_art.py --slug foo-bar  # one article
    python tools/make_article_art.py --limit 3       # first N missing
    python tools/make_article_art.py --force --slug foo-bar   # regenerate one
    python tools/make_article_art.py --dry-run       # print prompts only

Images are 1200x630 JPEGs (the og:image size the templates expect). Output
goes to src/static/images/articles/ and is committed; Railway never calls
this script. Cost is about $0.05 per image on the default (quality) model.
Requires only the standard library; cropping uses macOS `sips` when present.

To give a new article a specific scene, add its slug to SCENES below.
Articles without an entry get a scene picked from their topic label.
"""
import argparse, base64, json, os, pathlib, re, shutil, subprocess, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "articles"
OUT = ROOT / "src" / "static" / "images" / "articles"
API = "https://api.x.ai/v1/images/generations"
DEFAULT_MODEL = "grok-imagine-image-quality"

STYLE = (
    "Photorealistic editorial news photograph, shot on a full-frame DSLR with a 50mm lens, "
    "natural light, realistic colors, shallow depth of field, no text overlays, no watermark, "
    "no logos, no visible faces (hands, backs, or silhouettes are fine), "
    "wide horizontal composition suitable for a website header. Scene: "
)

# Per-article scenes. Keep faces out of frame; prefer objects, places, hands.
SCENES = {
    "medicare-part-d-2100-out-of-pocket-cap-2026":
        "Orange prescription bottles and a weekly pill organizer on a kitchen counter beside a pharmacy receipt and a calculator, soft morning window light.",
    "working-while-collecting-social-security-2026-earnings-test":
        "An older worker's hands (no face) in a plain apron holding a paycheck stub at a workbench in a small workshop, generic unbranded tools and plain cardboard boxes, no logos or product packaging, warm indoor light.",
    "how-to-appeal-a-denied-medicare-claim":
        "A stack of medical bills and an insurance statement stamped with a red 'DENIED' style mark on a desk, reading glasses and a highlighter beside them, a landline phone in soft focus.",
    "social-security-2027-cola-what-to-expect":
        "An older person's hands holding a government benefit envelope and a folded check at a wooden kitchen table, a coffee mug and reading glasses nearby, morning light through curtains.",
    "adult-child-moved-back-home-house-rules":
        "A suburban house front porch with moving boxes and a duffel bag stacked by the door, a second car in the driveway, late-afternoon light, no people.",
    "three-retirement-rules-changed-2026":
        "The United States Capitol building in Washington DC at golden hour, front view across the lawn, flag on the dome, no people in frame.",
    "medicare-open-enrollment-2026-checklist":
        "A red-white-and-blue Medicare-style card, an open laptop showing a blurred plan comparison, a printed checklist with checkboxes, and a pen on a dining table.",
    "social-security-overpayment-letter-what-to-do":
        "A single official-looking letter on Social Security style letterhead lying open on a kitchen table, an older person's hand resting beside it, reading glasses folded on top, muted light.",
    "required-minimum-distributions-before-73-checklist":
        "A retirement account statement, a desk calendar turned to December, a calculator and a fountain pen on a home office desk, warm lamp light.",
    "obituary-scams-grandparent-scams-seniors":
        "A newspaper open to the obituaries page on a kitchen table beside a ringing landline phone, reading glasses and a cup of tea, soft window light.",
    "medicare-part-d-premiums-2027-subsidy-ending":
        "A pharmacy counter with prescription bags and a card reader, blurred shelves of medicine behind, a customer's hand holding an insurance card, no faces.",
    "senior-discounts-you-have-to-ask-for":
        "A checkout counter with a receipt and a wallet, a hand holding out a membership card to a cashier, a coffee shop or grocery store background in soft focus.",
    "social-security-40-percent-replacement-what-to-do":
        "A kitchen table budget session: a paper household budget sheet, a calculator, a Social Security statement, a jar of coins and a mug, overhead angle, natural light.",
    "medicare-advantage-plan-leaving-county-what-to-do":
        "A rural county road sign and mailbox in front of a small-town clinic building, a letter sticking out of the mailbox, overcast daylight, no people.",
    "aging-in-place-vs-assisted-living-costs-programs":
        "A bright home bathroom with a newly installed grab bar and walk-in shower, a hallway with a stair railing visible, clean and welcoming, no people.",
    "social-security-trust-fund-2032-what-it-means":
        "The Social Security Administration headquarters style government office building exterior with an American flag, dramatic cloudy sky, wide shot, no people.",
    "parent-credit-card-debt-after-death-who-pays":
        "A stack of credit card statements and a collection letter on a desk beside a framed photo turned face down, a cardboard box of file folders, soft sad light.",
    "selling-your-life-insurance-policy-life-settlements":
        "A life insurance policy document in a manila folder on a lawyer's desk, a pen, and a signed check partly visible, leather chair in background, warm office light.",
    "downsizing-in-retirement-hidden-costs":
        "A living room half packed into cardboard moving boxes, a 'For Sale' style real estate sign visible through the window, afternoon light, no people.",
    "is-750000-enough-to-retire-with-social-security":
        "A couple's hands (no faces) reviewing a retirement savings statement and a Social Security estimate on a porch table, a lake and trees in soft focus behind.",
    "6000-senior-tax-deduction-explained":
        "A federal income tax return form and a W-2 on a desk with a calculator, reading glasses, and a mug, overhead angle, clean natural light.",
    "jury-duty-scam-tap-to-pay-theft-seniors":
        "A smartphone showing an incoming call from an unknown number lying on a kitchen counter next to a gift card and a wallet, tense low light.",
    "social-security-october-2026-payment-calendar":
        "A wall calendar turned to October with two dates circled in red marker, a bank deposit slip and a pen on the counter below it, morning light.",
}

# Fallback scenes by topic keyword for articles not listed above.
TOPIC_SCENES = {
    "social security": "An older person's hands holding a government benefit envelope and a folded check at a kitchen table, reading glasses and a mug nearby.",
    "medicare": "A Medicare-style card, prescription bottles and a clipboard on a dining table, soft window light.",
    "tax": "A federal tax form, a calculator and a pen on a desk, overhead angle.",
    "scam": "A landline phone off the hook next to a gift card and a wallet on a kitchen counter, low light.",
    "home": "A tidy suburban house exterior with a porch and a small garden, afternoon light.",
    "discount": "A checkout counter with a receipt, a wallet and a membership card.",
    "retirement": "A porch table with a savings statement, a mug and reading glasses, trees in soft focus.",
}


def parse(path):
    text = path.read_text()
    head, _ = text.split("\n---\n", 1)
    meta = {}
    for line in head.lstrip("-\n").splitlines():
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m:
            meta[m.group(1)] = m.group(2).strip()
    return meta, text


def scene_for(meta):
    if meta["slug"] in SCENES:
        return SCENES[meta["slug"]]
    t = meta.get("topic", "").lower()
    for k, v in TOPIC_SCENES.items():
        if k in t:
            return v
    return "A kitchen table with an envelope, reading glasses and a mug, morning light."


def build_prompt(meta):
    return STYLE + scene_for(meta)


def generate(prompt, model, key):
    req = urllib.request.Request(
        API,
        data=json.dumps({"model": model, "prompt": prompt, "n": 1,
                         "aspect_ratio": "16:9", "response_format": "b64_json"}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.load(r)
            return base64.b64decode(d["data"][0]["b64_json"])
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")[:300]
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(5 * (attempt + 1)); continue
            raise SystemExit(f"xAI error {e.code}: {body}")


def fit_1200x630(path):
    """Resize to width 1200 and center-crop to 630 tall. Uses sips on macOS."""
    if not shutil.which("sips"):
        print("  (sips not found; image left at native size)")
        return
    subprocess.run(["sips", "--resampleWidth", "1200", str(path)], check=True, capture_output=True)
    subprocess.run(["sips", "-c", "630", "1200", str(path)], check=True, capture_output=True)


def set_image_field(path, text, rel):
    if re.search(r"^image:", text, re.M):
        text = re.sub(r"^image:.*$", f"image: {rel}", text, count=1, flags=re.M)
    else:
        text = re.sub(r"^(summary:.*)$", rf"\1\nimage: {rel}", text, count=1, flags=re.M)
    path.write_text(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", action="append", help="only this slug (repeatable)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="regenerate even if image exists")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    key = os.environ.get("XAI_API_KEY")
    if not key and not a.dry_run:
        sys.exit("Set XAI_API_KEY first (export XAI_API_KEY=xai-...)")
    OUT.mkdir(parents=True, exist_ok=True)

    done = 0
    for p in sorted(CONTENT.glob("*.md")):
        meta, text = parse(p)
        slug = meta["slug"]
        if a.slug and slug not in a.slug:
            continue
        rel = f"images/articles/{slug}.jpg"
        target = ROOT / "src" / "static" / rel
        if target.exists() and meta.get("image") == rel and not a.force:
            continue
        prompt = build_prompt(meta)
        print(f"{slug}\n  scene: {scene_for(meta)[:110]}...")
        if a.dry_run:
            continue
        target.write_bytes(generate(prompt, a.model, key))
        fit_1200x630(target)
        set_image_field(p, text, rel)
        print(f"  -> {rel} ({target.stat().st_size // 1024} KB)")
        done += 1
        if a.limit and done >= a.limit:
            break
    print(f"{done} image(s) generated")


if __name__ == "__main__":
    main()
