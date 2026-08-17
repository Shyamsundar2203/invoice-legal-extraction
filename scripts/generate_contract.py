from PIL import Image, ImageDraw
from pathlib import Path

img = Image.new("RGB", (900, 1100), (255, 255, 255))
draw = ImageDraw.Draw(img)

lines = [
    "MASTER SERVICES AGREEMENT",
    "",
    "This Agreement is made effective as of 01/15/2026, by and between:",
    '"Acme Global Tech Inc." (the Party A) and "Apex Legal Solutions Ltd" (the Party B).',
    "",
    "1. TERM DURATION",
    "The term of this agreement shall be 24 months from the effective date.",
    "",
    "2. CONFIDENTIALITY",
    "Each party agrees to keep all confidential information strictly secret and protected.",
    "",
    "3. TERMINATION",
    "This Agreement shall terminate upon 30 days written notice by either party.",
    "",
    "4. GOVERNING LAW & JURISDICTION",
    "This Agreement is governed by the laws of Delaware.",
]

y = 50
for line in lines:
    draw.text((50, y), line, fill=(20, 20, 20))
    y += 40

out_path = Path("data/sample/sample_contract.png")
out_path.parent.mkdir(parents=True, exist_ok=True)
img.save(out_path)
print("Successfully created sample_contract.png")
