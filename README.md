# prizecardvault.com — static rebuild

Self-contained static rebuild of the Prize Custom Card Vault site (the original was a Grok Build app,
now unpublished). No Grok, no framework, no external runtime dependencies (fonts are self-hosted).
Checkout stays on Squarespace: every Buy button goes to `https://shop.prizecardvault.com/shop/p/{slug}`.

## Layout
- `docs/` — **the published site** (GitHub Pages → Deploy from branch `main`, folder `/docs`). Contains `CNAME` (prizecardvault.com), `404.html`, `.nojekyll`.
  - `/` sports gallery · `/games` game gallery · `/shop` (+ `?kind=game`) · `/nfc` · `/reprint` · `/c/{slug}` card pages (271)
  - `cards/{slug}.jpg`, `cards/{slug}-back.jpg`, `cards/back.jpg`, `cards/thumbs/{slug}.jpg|webp` — same paths as the old site
  - `videos/{slug}.mp4` — living reels (real Grok Imagine videos). Mapped in `data/reels.json`: 14 old-site reels by `tools/import_reels.py`, new Imagine batches by `tools/add_reels.py`.
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
Never substitute pan/zoom (Ken Burns) videos made from stills.

### Adding a batch of new Imagine reels
Make a TSV of `slug<TAB>/path/to/grok-video-….mp4` (one per line, `#` comments ok) and run:

    python3 tools/add_reels.py /workspace/pilot-reels/batchNN-files.tsv

For each slug it archives the untouched original to `/workspace/reels-master/<slug>.mp4` (on the box only —
**never commit originals**), encodes `docs/videos/<slug>.mp4` (H.264 High, no audio, long side 960 px, faststart,
per-clip CRF 20–30 chosen to land at 2.5–3.2 MB, aiming 2.8 MB), checks it with ffprobe, merges it into
`data/reels.json` and rebuilds. Existing web copies are skipped unless `--force`; `--dry-run` only checks the TSV.
Budget: Pages publishes `docs/` (1 GB limit, and git history keeps every committed version), so ~2.8 MB × 271
reels ≈ 0.9 GB with the rest of the site — keep the default size window and avoid needless `--force` re-encodes.
The full-screen player uses `/cards/<slug>.jpg` as the poster and `object-fit: contain`, so landscape reels are
letterboxed, never cropped. Then commit `docs/ data/ tools/`, `git pull --rebase` (the stats workflow commits daily), push.

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
