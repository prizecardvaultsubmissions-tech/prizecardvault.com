#!/usr/bin/env python3
"""One-time: build data/cards.json from the 2026-09-07 capture of the old Grok-built site.

Sources (on the build box, not in the repo):
  /workspace/prizecardvault/cards_classified.json  - parsed cards-*.js catalog (271 cards)
  /workspace/prizecardvault/home.html / games.html - SSR grid order for sports / game tabs
"""
import json, re, html, pathlib
CAP = pathlib.Path('/workspace/prizecardvault')
ROOT = pathlib.Path(__file__).resolve().parent.parent
SHOP = 'https://shop.prizecardvault.com/shop/p/{slug}'

cards = json.load(open(CAP / 'cards_classified.json'))
by = {c['slug']: c for c in cards}

def order(fn):
    s = open(CAP / fn).read()
    grid = s[s.find('style="perspective:1200px"'):]
    return list(dict.fromkeys(re.findall(r'href="/c/([^"]+)"', grid)))

sports, games = order('home.html'), order('games.html')
assert set(sports) | set(games) == set(by), (len(sports), len(games))
out = []
for kind, slugs in (('sports', sports), ('game', games)):
    for i, s in enumerate(slugs):
        c = by[s]
        assert c['_kind'] == kind, s
        out.append({
            'slug': s, 'name': c['name'], 'nameJa': c.get('nameJa', ''), 'kind': kind,
            'rarity': c['rarity'], 'cost': c['cost'], 'realm': c.get('realm', ''),
            'blurb': c.get('blurb', ''), 'layout': c.get('layout', 'portrait'),
            'hasBack': bool(c.get('back')), 'set': 'vault-2026-09',
            'shopUrl': SHOP.format(slug=s), 'order': i,
        })
json.dump({'generatedFrom': 'prizecardvault.com capture 2026-09-07 (cards-CStn9wgk.js)',
           'pricing': {'nfc': 29.99, 'holo': 14.99, 'bulkDiscountNote': '12% off 5+ plates (old in-app checkout)'},
           'cards': out}, open(ROOT / 'data/cards.json', 'w'), ensure_ascii=False, indent=1)
print(len(sports), 'sports', len(games), 'game')
