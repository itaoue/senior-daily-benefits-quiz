#!/usr/bin/env python3
"""Generate one editorial SVG banner per topic (used when an article has no photo)."""
import pathlib, math
OUT = pathlib.Path(__file__).resolve().parent.parent / "src/static/images/topics"; OUT.mkdir(parents=True, exist_ok=True)
NAVY, NAVY_D, AMBER, ORANGE, CREAM = "#1B2E5A", "#0F1E3D", "#D4A017", "#D4521A", "#F8F4E8"
W, H = 1200, 630

def frame(inner, bg=NAVY):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{NAVY_D}"/><stop offset="1" stop-color="#2A4080"/></linearGradient>
<pattern id="dots" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="14" cy="14" r="1.6" fill="{AMBER}" opacity=".18"/></pattern></defs>
<rect width="{W}" height="{H}" fill="url(#g)"/><rect width="{W}" height="{H}" fill="url(#dots)"/>
<rect x="0" y="{H-14}" width="{W}" height="14" fill="{AMBER}"/>
{inner}</svg>'''

def coins():  # Social Security: stack of coins + rising bars
    s = ""
    for i, hgt in enumerate([120, 180, 250, 330]):
        x = 700 + i*110; s += f'<rect x="{x}" y="{520-hgt}" width="80" height="{hgt}" rx="10" fill="{AMBER}" opacity="{.35+i*.2}"/>'
    for i in range(6):
        s += f'<ellipse cx="330" cy="{470-i*34}" rx="150" ry="34" fill="{AMBER if i%2 else "#E8B830"}" stroke="{NAVY_D}" stroke-width="4"/>'
    s += f'<text x="330" y="482" text-anchor="middle" font-family="Georgia,serif" font-size="46" font-weight="bold" fill="{NAVY_D}">$</text>'
    return s
def medical():  # Medicare: cross + shield
    return (f'<path d="M600 90 L820 160 V330 C820 440 720 520 600 560 C480 520 380 440 380 330 V160 Z" fill="{CREAM}" stroke="{AMBER}" stroke-width="10"/>'
            f'<rect x="555" y="220" width="90" height="230" rx="16" fill="{ORANGE}"/><rect x="485" y="290" width="230" height="90" rx="16" fill="{ORANGE}"/>')
def taxes():  # ledger + percent
    return (f'<rect x="300" y="110" width="420" height="420" rx="24" fill="{CREAM}" stroke="{AMBER}" stroke-width="10"/>'
            + "".join(f'<rect x="350" y="{170+i*70}" width="{300 if i%2 else 220}" height="18" rx="9" fill="{NAVY}" opacity=".35"/>' for i in range(5))
            + f'<circle cx="820" cy="330" r="150" fill="{ORANGE}"/><text x="820" y="372" text-anchor="middle" font-family="Georgia,serif" font-size="150" font-weight="bold" fill="{CREAM}">%</text>')
def home():  # house + bolt
    return (f'<path d="M600 110 L900 340 H840 V540 H360 V340 H300 Z" fill="{CREAM}" stroke="{AMBER}" stroke-width="10" stroke-linejoin="round"/>'
            f'<rect x="540" y="400" width="120" height="140" rx="8" fill="{NAVY}"/><rect x="400" y="380" width="90" height="90" rx="8" fill="{AMBER}"/><rect x="710" y="380" width="90" height="90" rx="8" fill="{AMBER}"/>'
            f'<path d="M640 200 L590 300 H640 L610 380 L690 260 H640 Z" fill="{ORANGE}"/>')
def discounts():  # price tag
    return (f'<g transform="rotate(-18 600 330)"><path d="M380 250 L620 170 L860 250 L860 470 L380 470 Z" fill="{CREAM}" stroke="{AMBER}" stroke-width="10" stroke-linejoin="round"/>'
            f'<circle cx="620" cy="235" r="22" fill="{NAVY}"/><text x="620" y="415" text-anchor="middle" font-family="Georgia,serif" font-size="130" font-weight="bold" fill="{ORANGE}">-15%</text></g>')
def scam():  # shield + exclamation + phone
    return (f'<path d="M600 90 L820 160 V330 C820 440 720 520 600 560 C480 520 380 440 380 330 V160 Z" fill="{CREAM}" stroke="{ORANGE}" stroke-width="10"/>'
            f'<rect x="570" y="190" width="60" height="200" rx="20" fill="{ORANGE}"/><circle cx="600" cy="450" r="34" fill="{ORANGE}"/>'
            f'<rect x="880" y="200" width="150" height="280" rx="24" fill="{NAVY_D}" stroke="{AMBER}" stroke-width="8"/><circle cx="955" cy="450" r="12" fill="{AMBER}"/>')
def general():
    return (f'<circle cx="600" cy="320" r="190" fill="{CREAM}" stroke="{AMBER}" stroke-width="10"/>'
            f'<path d="M520 330 L580 390 L690 250" fill="none" stroke="{ORANGE}" stroke-width="34" stroke-linecap="round" stroke-linejoin="round"/>')

ART = {"social-security": coins, "medicare": medical, "taxes": taxes, "home": home, "discounts": discounts, "scams": scam, "general": general}
for name, fn in ART.items():
    (OUT / f"{name}.svg").write_text(frame(fn()))
print("wrote", ", ".join(ART))
