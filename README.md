# prizecardvault.com — static rebuild

Self-contained static rebuild of the Prize Custom Card Vault site (the original was a Grok Build app,
now unpublished). No Grok, no framework, no external runtime dependencies (fonts are self-hosted).
Checkout stays on Squarespace: every Buy button goes to `https://shop.prizecardvault.com/shop/p/{slug}`.

## Layout
- `docs/` — **the published site** (GitHub Pages → Deploy from branch `main`, folder `/docs`). Contains `CNAME` (prizecardvault.com), `404.html`, `.nojekyll`.
  - `/` sports gallery · `/games` game gallery · `/shop` (+ `?kind=game`) · `/nfc` · `/reprint` · `/c/{slug}` card pages (271)
  - `cards/{slug}.jpg`, `cards/{slug}-back.jpg`, `cards/back.jpg`, `cards/thumbs/{slug}.jpg|webp` — same paths as the old site
  - `videos/{slug}.mp4` — living reels (real Grok Imagine videos from the old site; 14). Mapped in `data/reels.json` by `tools/import_reels.py`.
- `data/cards.json` — catalog (271 cards; order, rarity, blurbs, shop URL). `data/image-dims.json` — image sizes. `data/reels.json` — slug → living reel.
- `src/styles.css`, `src/app.js` — copied into `docs/assets/` by the build.
- `build.py` — generates all HTML. `python3 build.py`
- `tools/prepare_data.py`, `tools/process_images.py` — one-time import from the box capture (not needed to rebuild HTML).
- `tools/serve.py` — local preview that mimics GitHub Pages (`/c/slug` → `c/slug.html`, 404.html fallback): `python3 tools/serve.py 8765`
- `tools/crawl.py` — broken-link crawler against the preview.
- `data/staged-sets.md` — unpublished sets and how to add them.

## Full screen / living reels
The card page **Full screen** button opens a full-screen player: cards with a reel (`data/reels.json`) play it muted,
looping and `playsinline` (works on iPhone); cards without a reel show the plate image (current face) full screen.
Uses element `requestFullscreen` where supported, otherwise a fixed full-viewport overlay (iPhone). ✕ / Esc closes.
To add reels: put the real Grok Imagine MP4 in `tools/import_reels.py` SOURCES, run it, then `python3 build.py`.
Never substitute pan/zoom (Ken Burns) videos made from stills.

## Why `c/{slug}.html`
GitHub Pages serves `/c/drake-maye` from `c/drake-maye.html` without a redirect, so NFC chips already
written with `https://prizecardvault.com/c/{slug}` keep working. `/c/{slug}/` is caught by 404.html and redirected.

## Stats tab (sports cards)
Every sports card page has a **Card | Stats** switch (`/c/{slug}#stats` deep-links). The tab renders
`docs/data/stats/{slug}.json` client-side — the site stays fully static.
- `data/player-ids.json` — card → player mapping (`matched` with ESPN/MLB/NASCAR id, or `unmatched` + reason → "Stats coming soon"). Hand-editable.
- `tools/seed_player_ids.py` — curated subjects/leagues for new cards (`--retry` re-queues no-confident-match entries).
- `tools/update_stats.py [--resolve]` — stdlib-only fetcher. Auto-matches only on exact name with a single candidate in the
  expected league (or team+position+jersey hint for common names); never guesses. Keeps the previous JSON if a fetch fails;
  rewrites a file only when numbers change (`updated` = last data change).
- `.github/workflows/stats.yml` — runs daily (10:23 UTC) + manual dispatch; commits changed JSON (Pages redeploys).
Sources: ESPN public JSON (NFL/NBA/WNBA/NHL/soccer), MLB StatsAPI, NASCAR public CDN feed (2024+).
