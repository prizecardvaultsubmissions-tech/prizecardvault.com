# prizecardvault.com — static rebuild

Self-contained static rebuild of the Prize Custom Card Vault site (the original was a Grok Build app,
now unpublished). No Grok, no framework, no external runtime dependencies (fonts are self-hosted).
Checkout stays on Squarespace: every Buy button goes to `https://shop.prizecardvault.com/shop/p/{slug}`.

## Layout
- `docs/` — **the published site** (GitHub Pages → Deploy from branch `main`, folder `/docs`). Contains `CNAME` (prizecardvault.com), `404.html`, `.nojekyll`.
  - `/` sports gallery · `/games` game gallery · `/shop` (+ `?kind=game`) · `/nfc` · `/reprint` · `/c/{slug}` card pages (271)
  - `cards/{slug}.jpg`, `cards/{slug}-back.jpg`, `cards/back.jpg`, `cards/thumbs/{slug}.jpg|webp` — same paths as the old site
  - `videos/{slug}.mp4` — living reels that survived (8)
- `data/cards.json` — catalog (271 cards; order, rarity, blurbs, shop URL). `data/image-dims.json` — image sizes + reel list.
- `src/styles.css`, `src/app.js` — copied into `docs/assets/` by the build.
- `build.py` — generates all HTML. `python3 build.py`
- `tools/prepare_data.py`, `tools/process_images.py` — one-time import from the box capture (not needed to rebuild HTML).
- `tools/serve.py` — local preview that mimics GitHub Pages (`/c/slug` → `c/slug.html`, 404.html fallback): `python3 tools/serve.py 8765`
- `tools/crawl.py` — broken-link crawler against the preview.
- `data/staged-sets.md` — unpublished sets and how to add them.

## Why `c/{slug}.html`
GitHub Pages serves `/c/drake-maye` from `c/drake-maye.html` without a redirect, so NFC chips already
written with `https://prizecardvault.com/c/{slug}` keep working. `/c/{slug}/` is caught by 404.html and redirected.
