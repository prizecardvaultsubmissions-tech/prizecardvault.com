# Staged sets — NOT published on the static site (as of 2026-09-26)

The generator only publishes the 271 cards that were live on prizecardvault.com (capture 2026-09-07)
and that have per-plate Squarespace products at https://shop.prizecardvault.com/shop/p/{slug}.

| Set | Assets on box | Staging status (from notes) | Shop products? | Decision |
|---|---|---|---|---|
| Top 25 Egawa (39) | /workspace/prize-cards/top25-egawa/vault-ready (fronts+backs) | VAULT_STAGING.md: "Live site publish is NOT done — staging only"; NFL-shield scrub still open on 3 FIX fronts | 404 (e.g. brock-bowers-seam-threat, tj-watt-blitz-prism) | Excluded |
| NASCAR Chase 2026 (30) | /workspace/nascar-chase-2026/vault-ready (+ slug-map.csv) | PUBLISH_CHECKLIST.md: all boxes open, incl. "Confirm final art approval" | 404 (denny-hamlin-victory-lane) | Excluded |
| Top 100 gaps (30) | /workspace/prize-cards/top100-gaps/vault-ready | MANIFEST: "staging only; live publish NOT done" | 404 (caitlin-clark, aaron-judge) | Excluded |
| Holiday Havoc MLB (10 winners / 30 gens) | /workspace/prize-cards/holiday-havoc-mlb (PNG fronts only, no backs, no vault-ready) | Not staged | none | Excluded |
| JH Multiversal backs | /workspace/jh-multiversal-backs (PDF/preview only) | Backs for existing JH fronts; no per-slug JPGs | n/a | Excluded (existing JH cards keep their current backs) |

To publish a set later: create its Squarespace products (slug = vault slug), add entries to
data/cards.json (same fields as existing cards, `set` name, `hasBack`), run the image step for the
new slugs (tools/process_images.py reads fronts/backs; point SRC at the set's vault-ready folder), then `python3 build.py`.
