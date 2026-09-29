#!/usr/bin/env python3
"""Static site generator for prizecardvault.com (GitHub Pages).

  python3 build.py            -> regenerates HTML/CSS/JS into docs/
Inputs: data/cards.json, data/image-dims.json, data/reels.json, src/styles.css, src/app.js
Card images already live in docs/cards (see tools/process_images.py).
URLs: /c/{slug} is served from docs/c/{slug}.html (GitHub Pages resolves extensionless URLs),
so NFC chips already written with https://prizecardvault.com/c/{slug} keep working.
"""
import hashlib, html, json, pathlib, shutil
ROOT = pathlib.Path(__file__).resolve().parent
DOCS = ROOT / 'docs'
SITE = 'https://prizecardvault.com'
SHOP = 'https://shop.prizecardvault.com'
EMAIL = 'prizecardvaultsubmissions@gmail.com'
data = json.load(open(ROOT / 'data/cards.json'))
DIMS = json.load(open(ROOT / 'data/image-dims.json'))
# living reels: slug -> {'src': '/videos/{slug}.mp4', ...} (tools/import_reels.py)
REELS = {k: v for k, v in json.load(open(ROOT / 'data/reels.json'))['reels'].items()
         if (DOCS / v['src'].lstrip('/')).is_file()}
NFC_P, HOLO_P = data['pricing']['nfc'], data['pricing']['holo']
cards = [c for c in data['cards'] if c.get('published', True)]
sports = [c for c in cards if c['kind'] == 'sports']
games = [c for c in cards if c['kind'] == 'game']
e = lambda s: html.escape(str(s), quote=True)
money = lambda v: f'${v:.2f}'

ICONS = {
 'back': '<path d="m15 18-6-6 6-6"/>',
 'bag': '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/>',
 'scan': '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>',
 'down': '<path d="m6 9 6 6 6-6"/>',
 'box': '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
 'layers': '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z"/><path d="M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12"/><path d="M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17"/>',
 'flip': '<path d="M8 3H5a2 2 0 0 0-2 2v14c0 1.1.9 2 2 2h3"/><path d="M16 3h3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-3"/><path d="M12 20v2"/><path d="M12 14v2"/><path d="M12 8v2"/><path d="M12 2v2"/>',
 'reset': '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
 'play': '<polygon points="6 3 20 12 6 21 6 3"/>',
 'max': '<polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" x2="14" y1="3" y2="10"/><line x1="3" x2="10" y1="21" y2="14"/>',
 'copy': '<rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
}
def icon(n, sw='1.6'):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[n]}</svg>'

def asset_ver(p):
    return hashlib.sha1(p.read_bytes()).hexdigest()[:10]

def head(title, desc, path, image='/og.jpg', extra=''):
    canon = SITE + ('' if path == '/' else path)
    img = image if image.startswith('http') else SITE + image
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="#09080c">
<link rel="canonical" href="{canon}">
<meta property="og:site_name" content="Prize Card Vault">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="apple-mobile-web-app-title" content="Prize Card Vault">
<meta name="apple-mobile-web-app-status-bar-style" content="black">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preload" href="/assets/fonts/cormorant-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/fonts/fonts.css">
<link rel="stylesheet" href="/assets/styles.css?v={CSS_V}">
{extra}</head>
'''

def header(active=None, back=None, clear=False, tabs=True):
    left = (f'<a aria-label="Back" href="{back}" class="icon-btn">{icon("back")}</a>' if back else '<div class="spacer"></div>')
    cur = ' aria-current="page"' if active == 'home' else ''
    t = ''
    if tabs:
        t = (f'<nav aria-label="Card collection" class="tabs">'
             f'<a class="pill{" on" if active in ("home","sports") else ""}" href="/"{cur}>Sports cards</a>'
             f'<a class="pill{" on" if active in ("games","game") else ""}" href="/games">Game cards</a></nav>')
    return f'''<header class="site-header{' clear' if clear else ''}"><div class="hbar">{left}<a class="brand" href="/"><p class="t">Prize Custom Card Vault</p><p class="d">prizecardvault.com</p></a><div style="display:flex;align-items:center"><a aria-label="Shop" title="Shop plates" href="/shop" class="icon-btn">{icon("bag")}</a><a aria-label="NFC programming" title="NFC programming" href="/nfc" class="icon-btn">{icon("scan")}</a></div></div>{t}</header>'''

def footer():
    return f'''<footer class="site-foot"><nav><a href="/">Sports cards</a><a href="/games">Game cards</a><a href="/shop">Shop</a><a href="/reprint">Reprint with NFC</a><a href="/nfc">Program chips</a><a href="{SHOP}">shop.prizecardvault.com</a></nav><p>© Prize Custom Trading Cards · Checkout hosted by Squarespace at shop.prizecardvault.com</p></footer>'''

def tail():
    return f'<script src="/assets/app.js?v={JS_V}" defer></script>\n</body>\n</html>\n'

def thumb(c, cls=''):
    w, h = DIMS[c['slug']]['thumb']
    return (f'<picture><source type="image/webp" srcset="/cards/thumbs/{c["slug"]}.webp">'
            f'<img src="/cards/thumbs/{c["slug"]}.jpg" alt="{e(c["name"])}" width="{w}" height="{h}" loading="lazy" decoding="async" draggable="false"{cls}></picture>')

def tile(c):
    return (f'<a href="/c/{c["slug"]}" class="tile" data-rarity="{c["rarity"]}">{thumb(c)}<span class="shine"></span>'
            f'<span class="cap"><span class="nm">{e(c["name"])}</span><span class="rar foil {c["rarity"]}">{c["rarity"]} · {c["cost"]}</span></span></a>')

def gallery_page(kind):
    lst = sports if kind == 'sports' else games
    ur = sum(1 for c in lst if c['rarity'] == 'UR'); ssr = sum(1 for c in lst if c['rarity'] == 'SSR')
    if kind == 'sports':
        title, path, h1 = 'Prize Custom Card Vault', '/', 'Sports cards'
        lede = 'Hold each prize card in 3D, flip it in the hand, or open the 2D plate and pinch to inspect. Full-art game cards live on their own tab.'
        stats = f'<span>{len(lst)} sports</span><span>{ur} UR</span><span>{ssr} SSR</span>'
        acts = (f'<a href="/shop" class="pill solid">Shop sports</a><a href="/games" class="pill ghost">Game cards</a>'
                f'<a href="/reprint" class="pill ghost">Reprint with NFC</a><a href="/nfc" class="pill quiet">{icon("scan","1.7")}Program chips</a>'
                f'<a href="{SHOP}" class="pill quiet">Shop on Squarespace</a>')
        desc = 'Hold, flip, and scan foil prize cards in 3D. Each card has its own NFC link at prizecardvault.com.'
        active = 'home'
    else:
        title, path, h1 = 'Game cards · Prize Custom Card Vault', '/games', 'Game cards'
        lede = 'Full-art prize plates — original oils, legends, and living reels. Sports cards stay on the front of the vault.'
        stats = f'<span>{len(lst)} game cards</span><span>{ur} UR</span><span>{ssr} SSR</span>'
        acts = '<a href="/shop?kind=game" class="pill solid">Shop game cards</a><a href="/" class="pill ghost">Sports cards</a>'
        desc = 'Full-art game prize plates — original oils, legends, and living reels — each with its own NFC link.'
        active = 'games'
    gid = f'grid-{kind}'
    body = f'''<body>
<main>
{header(active)}
<section class="hero"><div class="in"><p class="eyebrow">prizecardvault.com</p><h1>{h1}</h1><p class="lede">{lede}</p><div class="stats">{stats}</div><div class="actions">{acts}</div></div></section>
<section class="wrap"><div class="gbar"><p data-count>{len(lst)} cards</p><div class="filters" data-filters="{gid}"><button type="button" class="on" data-filter="ALL">ALL</button><button type="button" data-filter="UR">UR</button><button type="button" data-filter="SSR">SSR</button></div></div>
<div class="grid" id="{gid}">{"".join(tile(c) for c in lst)}</div></section>
</main>
{footer()}
'''
    return head(title, desc, path) + body + tail()

def shop_page():
    def art(c):
        return (f'<article class="prod"><a href="/c/{c["slug"]}">{thumb(c)}</a><div class="b"><p class="n">{e(c["name"])}</p>'
                f'<p class="p">{money(HOLO_P)} holo · {money(NFC_P)} NFC</p><div class="buy">'
                f'<a class="btn sm primary" href="{e(c["shopUrl"])}" rel="noopener">NFC {money(NFC_P)}</a>'
                f'<a class="btn sm" href="{e(c["shopUrl"])}" rel="noopener">Holo {money(HOLO_P)}</a></div></div></article>')
    body = f'''<body>
<main data-shop>
{header(None, back='/', tabs=False)}
<section class="shop-head"><p class="eyebrow">Physical plates · NFC or holographic</p>
<h1 data-kind-text data-sports="Shop sports" data-game="Shop game cards">Shop sports</h1>
<p class="lede">Choose an <span class="hl">NFC plate</span> at {money(NFC_P)} with a chip encoded to its 3D page — not holographic — or an <span class="hl">unchipped holographic</span> at {money(HOLO_P)}, foil print with no chip. Pick the finish on the product page; checkout is hosted by Squarespace.</p>
<div class="actions" style="justify-content:flex-start"><a class="pill on" data-kind-tab="sports" href="/shop?kind=sports">Sports plates</a><a class="pill" data-kind-tab="game" href="/shop?kind=game">Game plates</a><a class="pill ghost" href="/reprint">Reprint your own card</a></div></section>
<section class="wrap">
<div class="shop-grid" data-kind-panel="sports">{"".join(art(c) for c in sports)}</div>
<div class="shop-grid hidden" data-kind-panel="game">{"".join(art(c) for c in games)}</div>
</section>
</main>
{footer()}
'''
    return head('Shop plates · Prize Custom Card Vault', f'Physical Prize Card Vault plates: NFC plate {money(NFC_P)} or unchipped holographic {money(HOLO_P)}. Checkout on shop.prizecardvault.com.', '/shop') + body + tail()

def nfc_page():
    items = ''.join(
        f'<li id="{c["slug"]}"><div><a href="/c/{c["slug"]}">{e(c["name"])}</a><p>{SITE}/c/{c["slug"]}</p></div>'
        f'<button type="button" class="btn sm" style="flex:0 0 auto" data-copy="{SITE}/c/{c["slug"]}">{icon("copy")}Copy</button></li>'
        for c in games + sports)  # same order as the old page (game list first, then sports)
    body = f'''<body>
<main>
{header(None, back='/', tabs=False)}
<article class="page"><p class="eyebrow">Field kit</p><h1>Program an NFC chip</h1>
<p class="lede">Each prize card has a permanent URL on <span style="color:var(--fg)">prizecardvault.com</span> at <code>/c/…</code>. Write that full URL to an NTAG213, NTAG215, or NTAG216 chip, then embed the chip in the physical card. A phone tap opens the 3D vault page for that card.</p>
<ol class="steps"><li>1. Copy the card URL below.</li><li>2. Open an NFC writer (NXP TagWriter, NFC Tools, or the Write chip button on Android Chrome).</li><li>3. Write a URL / URI record. Do not add extra path segments.</li><li>4. Confirm with a tap. The phone should land on that card’s 3D view.</li></ol>
<input class="search" type="search" placeholder="Filter {len(cards)} cards…" aria-label="Filter cards" data-search>
<ul class="urls" id="nfc-list">{items}</ul></article>
</main>
{footer()}
'''
    return head('Program an NFC chip · Prize Custom Card Vault', 'Write a prizecardvault.com/c/… card URL to an NTAG213/215/216 chip so a phone tap opens that card’s 3D vault page.', '/nfc') + body + tail()

def reprint_page():
    subj = 'Reprint request (NFC plate)'
    body = f'''<body>
<main>
{header(None, back='/shop', tabs=False)}
<section class="page"><p class="eyebrow">NFC chip embedded · {money(NFC_P)} each</p><h1>Reprint a plate</h1>
<p class="lede">Submit a front (back optional). We print the physical card, embed an NFC chip pointed at its 3D vault page, and invoice the order. Five or more copies take 12% off the cards.</p>
<div class="panel"><h2>How to order</h2>
<ol class="steps"><li>1. Email your artwork — front required, back optional — plus the card name and number of copies to <a href="mailto:{EMAIL}?subject={e(subj)}" style="color:var(--fg);text-decoration:underline">{EMAIL}</a>.</li>
<li>2. We confirm the proof and the vault URL your chip will open.</li>
<li>3. Pay for the reprint on the shop — one NFC reprint per copy.</li></ol>
<div class="actions" style="justify-content:flex-start"><a class="btn primary" href="{SHOP}/shop/p/nfc-reprint" rel="noopener">{icon("bag")}Order NFC reprint · {money(NFC_P)}</a><a class="btn" href="mailto:{EMAIL}?subject={e(subj)}">Email artwork</a><a class="btn" href="/shop">Shop the public catalog</a></div></div>
</section>
</main>
{footer()}
'''
    return head('Reprint with NFC · Prize Custom Card Vault', f'Reprint your own card art as a physical plate with an embedded NFC chip — {money(NFC_P)} each, 12% off 5+.', '/reprint') + body + tail()

def card_page(c):
    s = c['slug']; d = DIMS[s]
    fw, fh = d['front']
    back = f'/cards/{s}-back.jpg' if c['hasBack'] else '/cards/back.jpg'
    land = fw > fh
    ar = f'{fw}/{fh}'
    kicker = ' · '.join(x for x in (c['realm'], c['nameJa']) if x)
    reel = REELS.get(s, {}).get('src', '')
    vid = f'<video src="{reel}" muted loop playsinline preload="none" aria-hidden="true"></video>' if reel else ''
    reel_btn = f'<button type="button" class="btn" data-act="reel" aria-pressed="false">{icon("play")}Living reel</button>' if vid else ''
    kind_back = '/' if c['kind'] == 'sports' else '/games'
    viewtabs = stats_panel = ''
    if c['kind'] == 'sports':
        viewtabs = ('<div class="viewtabs" role="tablist" aria-label="Card view">'
                    '<button type="button" role="tab" id="tab-card" aria-controls="card-view" aria-selected="true" data-view="card">Card</button>'
                    '<button type="button" role="tab" id="tab-stats" aria-controls="stats" aria-selected="false" data-view="stats">Stats</button></div>')
        stats_panel = (f'<section class="stats-panel" id="stats" role="tabpanel" aria-labelledby="tab-stats" hidden data-src="/data/stats/{s}.json">'
                       f'<div class="stats-in"><p class="muted">Loading stats…</p>'
                       f'<noscript><p class="muted">Stats need JavaScript enabled.</p></noscript></div></section>')
    title = f'{c["name"]} · Prize Custom Card Vault'
    desc = (c['blurb'] or f'{c["name"]} prize card') + ' — hold it in 3D at prizecardvault.com.'
    jsonld = json.dumps({'@context': 'https://schema.org', '@type': 'Product', 'name': c['name'], 'image': f'{SITE}/cards/{s}.jpg',
        'description': c['blurb'], 'brand': {'@type': 'Brand', 'name': 'Prize Card Vault'}, 'url': f'{SITE}/c/{s}',
        'offers': {'@type': 'AggregateOffer', 'priceCurrency': 'USD', 'lowPrice': HOLO_P, 'highPrice': NFC_P, 'offerCount': 2, 'url': c['shopUrl']}}, ensure_ascii=False)
    extra = f'<link rel="preload" as="image" href="/cards/{s}.jpg">\n<script type="application/ld+json">{jsonld}</script>\n'
    body = f'''<body>
<main class="card-page">
{header(c['kind'], back=kind_back, clear=True)}
<div class="stage" id="card-view">{vid}<div class="vignette"></div>
{viewtabs}<div class="scene"><button type="button" class="hint" data-act="hint">Drag to turn · double-tap to bring forward</button>
<div class="card3d{' landscape' if land else ''}" style="--ar:{ar}" data-front="/cards/{s}.jpg" data-back="{back}" data-name="{e(c['name'])}">
<div class="card-face front"><img src="/cards/{s}.jpg" alt="{e(c['name'])}" width="{fw}" height="{fh}" draggable="false"><span class="shine"></span></div>
<div class="card-face back"><img src="{back}" alt="{e(c['name'])} — back" loading="lazy" draggable="false"></div>
</div></div>
{stats_panel}<div class="dock"><div class="in">
<button type="button" class="toggle" data-act="details" aria-expanded="true" aria-controls="card-info-dock">{icon("down")}<span>Hide details</span></button>
<div id="card-info-dock" class="info"><div>
<div class="row"><div style="min-width:0"><p class="kicker">{e(kicker)}</p><h1>{e(c['name'])}</h1></div>
<div class="chips"><span class="chip foil">{c['cost']}</span><span class="chip foil {c['rarity']}">{c['rarity']}</span></div></div>
<p class="blurb">{e(c['blurb'])}</p>
<div class="controls">
<button type="button" class="btn primary" data-act="d3">{icon("box")}3D</button>
<button type="button" class="btn" data-act="d2">{icon("layers")}2D</button>
<button type="button" class="btn" data-act="flip">{icon("flip")}Flip</button>
<button type="button" class="btn" data-act="reset">{icon("reset")}Reset</button>
{reel_btn}<button type="button" class="btn" data-act="fs" data-reel="{reel}" aria-haspopup="dialog" title="{'Play the living reel full screen' if reel else 'View the plate full screen'}">{icon("max")}Full screen</button>
<a class="btn" href="/nfc#{s}">NFC</a>
<a class="btn primary" href="{e(c['shopUrl'])}" rel="noopener">{icon("bag")}NFC {money(NFC_P)}</a>
<a class="btn" href="{e(c['shopUrl'])}" rel="noopener">Holo {money(HOLO_P)}</a>
</div></div></div></div></div>
</div>
</main>
'''
    return head(title, desc, f'/c/{s}', image=f'/cards/{s}.jpg', extra=extra) + body + tail()

def page_404():
    body = f'''<body>
<main>
{header(None, back='/', tabs=False)}
<section class="hero"><div class="in"><p class="eyebrow">404 · not in the vault</p><h1>This plate isn’t here</h1>
<p class="lede">The page you tapped may have moved. Browse the vault, or head to the shop for physical plates.</p>
<div class="actions"><a class="pill solid" href="/">Sports cards</a><a class="pill ghost" href="/games">Game cards</a><a class="pill ghost" href="/shop">Shop</a><a class="pill quiet" href="{SHOP}">shop.prizecardvault.com</a></div></div></section>
</main>
{footer()}
<script>
// Legacy routes from the old app: send them somewhere useful.
(function(){{var p=location.pathname.replace(/\\/+$/,'');
var m=p.match(/^\\/c\\/([a-z0-9-]+)(\\/.*)?$/);
if(m&&location.pathname!=='/c/'+m[1]){{location.replace('/c/'+m[1]+location.search+location.hash);return;}}
var map={{'/membership':'{SHOP}','/myprizecardvault':'{SHOP}','/checkout':'{SHOP}/cart','/cart':'{SHOP}/cart','/login':'/','/index.html':'/'}};
if(map[p])location.replace(map[p]);}})();
</script>
'''
    # absolute asset URLs so 404 renders at any depth
    return head('Not found · Prize Custom Card Vault', 'Page not found.', '/404') + body + tail()

FAVICON = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f3dfa6"/><stop offset=".5" stop-color="#c79a45"/><stop offset="1" stop-color="#f0d792"/></linearGradient></defs><rect width="64" height="64" rx="14" fill="#09080c"/><rect x="17" y="9" width="30" height="42" rx="5" fill="none" stroke="url(#g)" stroke-width="3" transform="rotate(-8 32 30)"/><text x="32" y="40" text-anchor="middle" font-family="Georgia,serif" font-size="22" font-weight="600" fill="url(#g)">P</text></svg>'''

def main():
    global CSS_V, JS_V
    (DOCS / 'assets').mkdir(parents=True, exist_ok=True)
    (DOCS / 'c').mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'src/styles.css', DOCS / 'assets/styles.css')
    shutil.copy2(ROOT / 'src/app.js', DOCS / 'assets/app.js')
    CSS_V, JS_V = asset_ver(DOCS / 'assets/styles.css'), asset_ver(DOCS / 'assets/app.js')
    w = lambda p, s: (DOCS / p).write_text(s, encoding='utf-8')
    w('index.html', gallery_page('sports'))
    w('games.html', gallery_page('game'))
    w('shop.html', shop_page())
    w('nfc.html', nfc_page())
    w('reprint.html', reprint_page())
    w('404.html', page_404())
    for old in (DOCS / 'c').glob('*.html'):
        old.unlink()
    for c in cards:
        w(f'c/{c["slug"]}.html', card_page(c))
    w('favicon.svg', FAVICON)
    w('CNAME', 'prizecardvault.com')  # same bytes as the file GitHub created (no newline)
    w('.nojekyll', '')
    w('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n')
    urls = ['/', '/games', '/shop', '/nfc', '/reprint'] + [f'/c/{c["slug"]}' for c in cards]
    w('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
      ''.join(f'<url><loc>{SITE}{"" if u == "/" else u}</loc></url>\n' for u in urls) + '</urlset>\n')
    print(f'built {5 + 1 + len(cards)} pages ({len(sports)} sports + {len(games)} game card pages); '
          f'{sum(1 for c in cards if c["slug"] in REELS)} cards with a living reel')

if __name__ == '__main__':
    main()
