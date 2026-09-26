#!/usr/bin/env python3
"""Crawl the local preview from / and check every internal link/asset + list external links."""
import re, sys, collections, urllib.request, urllib.parse, html
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765'
seen, queue, bad, external, checked = set(), ['/'], [], collections.Counter(), {}
ATTR = re.compile(r'''(?:href|src|data-front|data-back|poster)=["']([^"']+)["']|srcset=["']([^"']+)["']|url\(([^)]+)\)''')
def status(path):
    if path in checked: return checked[path]
    try:
        r = urllib.request.urlopen(urllib.request.Request(BASE + path, method='GET'), timeout=20)
        checked[path] = (r.status, r.read() if r.headers.get('Content-Type', '').startswith(('text/html', 'text/css')) else b'')
    except urllib.error.HTTPError as e:
        checked[path] = (e.code, b'')
    return checked[path]
pages = 0
while queue:
    p = queue.pop()
    if p in seen: continue
    seen.add(p)
    code, body = status(p)
    if code != 200: continue
    if not body: continue
    pages += 1 if p.endswith(('.html',)) or '.' not in p.rsplit('/', 1)[-1] else 0
    text = body.decode('utf-8', 'replace')
    for m in ATTR.finditer(text):
        vals = [m.group(1)] if m.group(1) else ([x.strip().split(' ')[0] for x in m.group(2).split(',')] if m.group(2) else [m.group(3).strip('\'" ')])
        for v in vals:
            v = html.unescape(v)
            if v.startswith(('mailto:', 'tel:', 'data:', '#', 'javascript:')): continue
            if v.startswith(('http://', 'https://')):
                if v.startswith('https://prizecardvault.com'):  # canonical/og self refs -> map to local
                    v = urllib.parse.urlparse(v).path or '/'
                else:
                    external[v] += 1; continue
            if not v.startswith('/'):
                v = urllib.parse.urljoin(p, v)
            v = v.split('#')[0]
            if not v: continue
            c, _ = status(v)
            if c != 200: bad.append((p, v, c))
            elif v not in seen: queue.append(v)
print(f'crawled {len(seen)} internal URLs ({pages} HTML pages); broken internal refs: {len(bad)}')
for b in bad[:50]: print('  BROKEN', b)
hosts = collections.Counter(urllib.parse.urlparse(u).netloc for u in external)
print('external link hosts:', dict(hosts))
open('/tmp/pcv-external.txt', 'w').write('\n'.join(sorted(external)))
