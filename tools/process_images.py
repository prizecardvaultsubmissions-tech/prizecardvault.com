#!/usr/bin/env python3
"""One-time: resize/optimize card art from the box into docs/ (web sizes).
full: <=1200px long side JPEG q82 (kept at old /cards/{slug}.jpg paths for NFC/eBay compat)
thumbs: 400px-wide JPEG + WebP at /cards/thumbs/{slug}.(jpg|webp)
"""
import json, pathlib, shutil, sys
from concurrent.futures import ProcessPoolExecutor
from PIL import Image, ImageOps
ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
SRC = pathlib.Path('/workspace/prize-cards/squarespace-import/images')
(DOCS / 'cards/thumbs').mkdir(parents=True, exist_ok=True)

def save_full(src, dst, maxside=1200):
    im = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
    im.thumbnail((maxside, maxside), Image.LANCZOS)
    im.save(dst, 'JPEG', quality=82, optimize=True, progressive=True)
    return im.size

def job(slug, has_back):
    dims = {}
    dims['front'] = save_full(SRC / 'front' / f'{slug}.jpg', DOCS / 'cards' / f'{slug}.jpg')
    im = Image.open(DOCS / 'cards' / f'{slug}.jpg')
    w = 400; h = round(im.height * w / im.width)
    t = im.resize((w, h), Image.LANCZOS)
    t.save(DOCS / 'cards/thumbs' / f'{slug}.jpg', 'JPEG', quality=80, optimize=True, progressive=True)
    t.save(DOCS / 'cards/thumbs' / f'{slug}.webp', 'WEBP', quality=78, method=6)
    dims['thumb'] = (w, h)
    if has_back:
        b = SRC / 'backs' / f'{slug}-back.jpg'
        dims['back'] = save_full(b, DOCS / 'cards' / f'{slug}-back.jpg')
    return slug, dims

if __name__ == '__main__':
    cards = json.load(open(ROOT / 'data/cards.json'))['cards']
    out = {}
    with ProcessPoolExecutor() as ex:
        for slug, d in ex.map(job, [c['slug'] for c in cards], [c['hasBack'] for c in cards]):
            out[slug] = d
    out['_default_back'] = {'back': save_full(SRC / 'backs' / 'back.jpg', DOCS / 'cards' / 'back.jpg')}
    # living reels: see tools/import_reels.py -> docs/videos/{slug}.mp4 + data/reels.json
    shots = pathlib.Path('/workspace/prize-cards/video-build/shots')
    shutil.copy2(shots / 'vault-og.jpg', DOCS / 'og.jpg')
    shutil.copy2(shots / 'vault-banner.jpg', DOCS / 'x-banner.jpg')
    json.dump(out, open(ROOT / 'data/image-dims.json', 'w'), indent=0)
    print(len(cards), 'cards')
