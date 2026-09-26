#!/usr/bin/env python3
"""Fetch player stats for the Stats tab -> docs/data/stats/{slug}.json  (stdlib only).

  python3 tools/update_stats.py --resolve   # look up IDs for "pending" entries in data/player-ids.json, then fetch
  python3 tools/update_stats.py             # fetch stats for all matched entries (daily job)

Sources (free, no key):
  NFL/NBA/WNBA/NHL: ESPN public site/core JSON (site.web.api.espn.com, sports.core.api.espn.com) - unofficial, undocumented
  MLB:              MLB StatsAPI (statsapi.mlb.com) - (c) MLB Advanced Media, non-commercial/individual use terms
  Soccer:           ESPN (club-league seasons via core API statisticslog)
  NASCAR:           NASCAR's public CDN feed (cf.nascar.com racinginsights points feed, 2024+) - EXPERIMENTAL, no NASCAR cards published yet
Rules: IDs are only auto-assigned on an exact (normalized) full-name match with exactly one candidate in the
expected league; anything else is flagged, never guessed. If a fetch fails the previous JSON is kept.
"""
import datetime as dt, json, pathlib, re, sys, time, unicodedata, urllib.parse, urllib.request, urllib.error
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs/data/stats'
IDS = ROOT / 'data/player-ids.json'
UA = 'PrizeCardVault-stats/1.0 (+https://prizecardvault.com; daily static-site refresh)'
ESPN_SPORT = {'nfl': 'football', 'nba': 'basketball', 'wnba': 'basketball', 'nhl': 'hockey'}
LEAGUE_LABEL = {'nfl': 'NFL', 'nba': 'NBA', 'wnba': 'WNBA', 'nhl': 'NHL', 'mlb': 'MLB', 'soccer': 'Soccer', 'nascar': 'NASCAR Cup'}
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
_last = [0.0]

def get(url, tries=4):
    for i in range(tries):
        wait = 0.35 - (time.time() - _last[0])
        if wait > 0: time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code in (404, 403): return None
            if i == tries - 1: raise
            time.sleep(2 ** i * (5 if e.code == 429 else 1))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if i == tries - 1: raise
            time.sleep(2 ** i)

def norm(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower()
    n = re.sub(r"[.'\u2019-]", '', n)
    n = re.sub(r'\b(jr|sr|ii|iii|iv|v)\b', '', n)
    return ' '.join(n.split())

# ---------------------------------------------------------------- ID resolution
def resolve(e):
    person, league = e.get('searchName') or e['person'], e['league']
    if league == 'mlb':
        d = get('https://statsapi.mlb.com/api/v1/people/search?names=' + urllib.parse.quote(person)) or {}
        cands = [p for p in d.get('people', []) if norm(p['fullName']) == norm(person)]
        if len(cands) > 1:
            cands = [p for p in cands if p.get('active')]
        ids = [(str(p['id']), p['fullName']) for p in cands]
    elif league == 'nascar':
        d = get('https://cf.nascar.com/cacher/drivers.json') or {}
        ids = [(str(p['Nascar_Driver_ID']), p['Full_Name'].strip()) for p in d.get('response', [])
               if norm(p['Full_Name']) == norm(person) and p.get('Driver_Series') == 'nascar-cup-series']
    else:
        want = {'soccer': None}.get(league, league)
        d = get('https://site.web.api.espn.com/apis/common/v3/search?type=player&limit=20&query=' + urllib.parse.quote(person)) or {}
        ids = []
        for it in d.get('items', []):
            if norm(it.get('displayName', '')) != norm(person): continue
            if league == 'soccer' and it.get('sport') != 'soccer': continue
            if want and it.get('league') != want: continue
            ids.append((it['id'], it['displayName']))
        ids = list(dict.fromkeys(ids))
        if len(ids) > 1 and e.get('hint') and league in ESPN_SPORT:
            h, keep = e['hint'], []
            for i, n in ids:
                a = (get(f'https://site.web.api.espn.com/apis/common/v3/sports/{ESPN_SPORT[league]}/{league}/athletes/{i}') or {}).get('athlete') or {}
                if ((a.get('team') or {}).get('abbreviation') == h.get('team') and (a.get('position') or {}).get('abbreviation') == h.get('position')
                        and str(a.get('jersey')) == str(h.get('jersey'))):
                    keep.append((i, n))
            if len(keep) == 1:
                e.update(status='matched', id=keep[0][0], matchedName=keep[0][1], matchedOn=NOW[:10],
                         match=f"{len(ids)} same-name candidates; disambiguated by team+position+jersey {h}")
                return e
    if len(ids) == 1:
        e.update(status='matched', id=ids[0][0], matchedName=ids[0][1], matchedOn=NOW[:10], match='exact-name, single candidate in league')
    else:
        e.update(status='unmatched', reason='no-confident-match',
                 note=f'{len(ids)} exact-name candidates in {league}: ' + ', '.join(f'{n} ({i})' for i, n in ids[:5]))
    return e

# ---------------------------------------------------------------- adapters -> normalized groups
def num(v):
    try: return float(str(v).replace(',', ''))
    except ValueError: return 0.0

def espn(league, pid):
    sport = ESPN_SPORT[league]
    base = f'https://site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{pid}'
    a = (get(base) or {}).get('athlete') or {}
    st = get(base + '/stats') or {}
    lg = get(f'https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}') or {}
    cur_year = (lg.get('season') or {}).get('year')
    cur_label = (lg.get('season') or {}).get('displayName') or str(cur_year)
    teams = {t['id']: t.get('abbreviation') for t in (st.get('teams') or {}).values()}
    skip = {'miscellaneous'}
    groups = []
    for c in st.get('categories', []):
        if c.get('name') in skip or not c.get('statistics'): continue
        labels = c.get('labels') or []
        tot = c.get('totals') or []
        # drop categories with nothing but zeros (e.g. a QB's kicking table)
        if tot and all(num(x) == 0 for x in tot[1:]): continue
        def season_label(y):
            return f'{y-1}-{str(y)[2:]}' if league in ('nba', 'wnba_', 'nhl') else str(y)
        rows = [{'season': season_label(s['season']['year']), 'year': s['season']['year'],
                 'team': teams.get(s.get('teamId'), s.get('teamSlug', '')), 'stats': s['stats']} for s in c['statistics']]
        cur = [r for r in rows if r['year'] == cur_year]
        groups.append({'key': c.get('name'), 'title': c.get('displayName') or c.get('name'), 'columns': labels, 'rows': rows,
                       'career': tot or None, 'current': cur[-1]['stats'] if cur else None})
    pos = (a.get('position') or {}).get('abbreviation') or ''
    if league == 'nfl':
        groups = nfl_filter(groups, st, pos)
    groups = groups[:4]
    if not groups: return None
    return {'player': {'name': a.get('displayName'), 'team': (a.get('team') or {}).get('displayName'),
                       'position': (a.get('position') or {}).get('abbreviation'), 'jersey': a.get('jersey')},
            'currentSeason': {'label': cur_label if league in ('nba', 'nhl') else str(cur_year), 'year': cur_year},
            'groups': groups,
            'source': {'name': 'ESPN', 'url': ((a.get('links') or [{}])[0]).get('href') or f'https://www.espn.com/{league}/player/_/id/{pid}'}}

NFL_KEEP = {  # categories that matter for a position, in display order
    'QB': ['passing', 'rushing'], 'RB': ['rushing', 'receiving'], 'FB': ['rushing', 'receiving'],
    'WR': ['receiving', 'rushing', 'returning'], 'TE': ['receiving'], 'K': ['kicking'], 'P': ['punting'],
}
NFL_DEF = {'DE', 'DT', 'NT', 'DL', 'LB', 'OLB', 'ILB', 'MLB', 'EDGE', 'CB', 'S', 'FS', 'SS', 'DB'}
NFL_OL = {'OT', 'T', 'G', 'OG', 'C', 'OL', 'LS'}

def nfl_filter(groups, st, pos):
    if pos in NFL_OL:   # linemen have no box-score stats; show games played per season
        src = max((g for g in groups), key=lambda g: len(g['rows']), default=None)
        if not src: return []
        return [{'key': 'games', 'title': 'Games played (seasons with a recorded stat)', 'columns': ['GP'], 'current': src['current'][:1] if src['current'] else None,
                 'rows': [dict(r, stats=r['stats'][:1]) for r in src['rows']], 'career': (src['career'] or [''])[:1]}]
    keep = ['defensive'] if pos in NFL_DEF else NFL_KEEP.get(pos)
    if not keep: return groups
    out = [g for k in keep for g in groups if g['key'] == k]
    # minor categories (e.g. a WR's 3 career carries) only if they have 3+ seasons of data
    return [g for i, g in enumerate(out) if i == 0 or len(g['rows']) >= 3] or groups[:1]

MLB_COLS = {
    'hitting': [('G', 'gamesPlayed'), ('AB', 'atBats'), ('R', 'runs'), ('H', 'hits'), ('2B', 'doubles'), ('3B', 'triples'),
                ('HR', 'homeRuns'), ('RBI', 'rbi'), ('SB', 'stolenBases'), ('BB', 'baseOnBalls'), ('SO', 'strikeOuts'),
                ('AVG', 'avg'), ('OBP', 'obp'), ('SLG', 'slg'), ('OPS', 'ops')],
    'pitching': [('G', 'gamesPlayed'), ('GS', 'gamesStarted'), ('W', 'wins'), ('L', 'losses'), ('SV', 'saves'),
                 ('IP', 'inningsPitched'), ('H', 'hits'), ('ER', 'earnedRuns'), ('BB', 'baseOnBalls'), ('SO', 'strikeOuts'),
                 ('ERA', 'era'), ('WHIP', 'whip')]}

_mlbt = {}
def mlb_teams():
    if not _mlbt:
        for season in (dt.date.today().year, dt.date.today().year - 5, dt.date.today().year - 10):
            for t in (get(f'https://statsapi.mlb.com/api/v1/teams?sportId=1&season={season}') or {}).get('teams', []):
                _mlbt.setdefault(t['id'], t.get('abbreviation'))
    return _mlbt

def mlb(pid):
    d = get(f'https://statsapi.mlb.com/api/v1/people/{pid}?hydrate=currentTeam,stats(group=[hitting,pitching],type=[yearByYear,career])')
    if not d or not d.get('people'): return None
    p = d['people'][0]
    pos = (p.get('primaryPosition') or {}).get('abbreviation')
    abbr = mlb_teams()
    cur_year = dt.date.today().year
    by = {}
    for s in p.get('stats', []):
        by.setdefault(s['group']['displayName'], {})[s['type']['displayName']] = s['splits']
    order = ['pitching', 'hitting'] if pos == 'P' else ['hitting', 'pitching']
    groups = []
    for g in order:
        splits = by.get(g, {}).get('yearByYear') or []
        if not splits or (g == 'hitting' and pos == 'P') or (g == 'pitching' and pos not in ('P', 'TWP')): continue
        cols = MLB_COLS[g]
        seasons = {}
        for sp in splits:
            seasons.setdefault(sp['season'], []).append(sp)
        rows = []
        for yr, sps in seasons.items():
            tot = [x for x in sps if not x.get('team')]
            for sp in (tot or sps):
                t = sp.get('team') or {}
                team = abbr.get(t.get('id')) or t.get('abbreviation') or t.get('name') or f"{sp.get('numTeams', 2)} teams"
                rows.append({'season': yr, 'year': int(yr), 'team': team, 'stats': [str(sp['stat'].get(k, '')) for _, k in cols]})
        car = (by.get(g, {}).get('career') or [{}])[0].get('stat')
        cur = [r for r in rows if r['year'] == cur_year]
        groups.append({'title': g.capitalize(), 'columns': [c for c, _ in cols], 'rows': rows,
                       'career': [str(car.get(k, '')) for _, k in cols] if car else None, 'current': cur[-1]['stats'] if cur else None})
    if not groups: return None
    return {'player': {'name': p.get('fullName'), 'team': (p.get('currentTeam') or {}).get('name'), 'position': pos,
                       'jersey': p.get('primaryNumber')},
            'currentSeason': {'label': str(cur_year), 'year': cur_year}, 'groups': groups,
            'source': {'name': 'MLB Stats API', 'url': f'https://www.mlb.com/player/{pid}'}}

SOCCER_COLS = [('Apps', 'appearances'), ('Starts', 'starts'), ('Min', 'minutes'), ('G', 'totalGoals'), ('A', 'goalAssists'),
               ('Shots', 'totalShots'), ('SOT', 'shotsOnTarget'), ('YC', 'yellowCards'), ('RC', 'redCards')]
SOCCER_NAMES = {'esp.1': 'LaLiga', 'fra.1': 'Ligue 1', 'usa.1': 'MLS', 'eng.1': 'Premier League', 'ger.1': 'Bundesliga', 'aut.1': 'Austrian Bundesliga', 'ita.1': 'Serie A'}

def soccer(pid, leagues):
    rows, a = [], {}
    for lg in leagues:
        log = get(f'https://sports.core.api.espn.com/v2/sports/soccer/leagues/{lg}/athletes/{pid}/statisticslog') or {}
        for ent in log.get('entries', []):
            yr = int(re.search(r'seasons/(\d{4})', ent['season']['$ref']).group(1))
            ref = next((x['statistics']['$ref'] for x in ent.get('statistics', []) if x.get('type') == 'total'), None)
            if not ref: continue
            sd = get(ref.replace('http://', 'https://')) or {}
            vals = {s['name']: s.get('displayValue') for c in (sd.get('splits') or {}).get('categories', []) for s in c.get('stats', [])}
            label = str(yr) if lg == 'usa.1' else f'{yr}-{str(yr + 1)[2:]}'
            rows.append({'season': label, 'year': yr, 'team': SOCCER_NAMES.get(lg, lg), 'stats': [vals.get(k, '0') for _, k in SOCCER_COLS]})
    rows = [r for r in rows if num(r['stats'][0]) > 0]   # ESPN has empty placeholder seasons; drop them
    if not rows: return None
    rows.sort(key=lambda r: r['year'])
    today = dt.date.today()
    last = rows[-1]
    euro_cur = today.year if today.month >= 7 else today.year - 1
    is_cur = last['year'] == (today.year if last['team'] == 'MLS' else euro_cur)
    car = [str(int(sum(num(r['stats'][i]) for r in rows))) for i in range(len(SOCCER_COLS))]
    base = f'https://site.web.api.espn.com/apis/common/v3/sports/soccer/{leagues[-1]}/athletes/{pid}'
    a = (get(base) or {}).get('athlete') or {}
    ov = (get(base + '/overview') or {}).get('statistics') or {}
    groups = [{'title': 'League seasons (club)', 'columns': [c for c, _ in SOCCER_COLS], 'rows': rows, 'career': car,
               'careerLabel': 'League career*', 'current': last['stats'] if is_cur else None}]
    if ov.get('splits'):
        groups.insert(0, {'title': 'Current season by competition', 'columns': ['Competition'] + ov.get('labels', []),
                          'rows': [{'season': sp['displayName'], 'year': 0, 'team': '', 'stats': sp['stats']} for sp in ov['splits']],
                          'career': None, 'current': None, 'plain': True})
    return {'player': {'name': a.get('displayName'), 'team': (a.get('team') or {}).get('displayName'),
                       'position': (a.get('position') or {}).get('abbreviation'), 'jersey': a.get('jersey')},
            'currentSeason': {'label': str(last['season']), 'year': last['year']}, 'groups': groups,
            'note': '*Career = sum of top-flight club league seasons available from ESPN (cups and internationals excluded; some early seasons lack minutes data).',
            'source': {'name': 'ESPN', 'url': f'https://www.espn.com/soccer/player/stats/_/id/{pid}'}}

NASCAR_COLS = [('Rank', 'position'), ('Pts', 'points'), ('Starts', 'starts'), ('Wins', 'wins'), ('Top 5', 'top_5'),
               ('Top 10', 'top_10'), ('Poles', 'poles'), ('Laps led', 'laps_led'), ('DNF', 'dnf')]

def nascar(pid):
    rows, y = [], dt.date.today().year
    for yr in range(2024, y + 1):   # public feed is available from 2024
        feed = get(f'https://cf.nascar.com/data/cacher/production/{yr}/1/racinginsights-points-feed.json') or []
        for r in feed:
            if str(r.get('driver_id')) == str(pid):
                rows.append({'season': str(yr), 'year': yr, 'team': f"#{r.get('car_no', '')} {r.get('manufacturer', '')}".strip(),
                             'stats': [str(r.get(k, '')) for _, k in NASCAR_COLS]})
    # the CDN sometimes serves the current feed under a past year's path; drop exact duplicates of a later year
    rows = [r for i, r in enumerate(rows) if not any(r['stats'] == q['stats'] for q in rows[i + 1:])]
    if not rows: return None
    car = [''] + [str(int(sum(num(r['stats'][i]) for r in rows))) for i in range(1, len(NASCAR_COLS))]
    return {'player': {'name': None, 'team': rows[-1]['team'], 'position': 'Driver', 'jersey': None},
            'currentSeason': {'label': str(y), 'year': y},
            'groups': [{'title': 'Cup Series seasons', 'columns': [c for c, _ in NASCAR_COLS], 'rows': rows, 'career': car,
                        'careerLabel': 'Since 2024*', 'current': next((r['stats'] for r in rows if r['year'] == y), None)}],
            'note': '*NASCAR\'s public feed covers 2024 onward.',
            'source': {'name': 'NASCAR', 'url': 'https://www.nascar.com/stats/'}}

def fetch(e):
    lg = e['league']
    if lg in ESPN_SPORT: return espn(lg, e['id'])
    if lg == 'mlb': return mlb(e['id'])
    if lg == 'soccer': return soccer(e['id'], e.get('leagues') or [])
    if lg == 'nascar': return nascar(e['id'])
    return None

# ---------------------------------------------------------------- main
def write(slug, doc):
    """Write only if stats changed; 'updated' = when the data last changed."""
    p = OUT / f'{slug}.json'
    old = json.loads(p.read_text()) if p.exists() else None
    if old and {k: v for k, v in old.items() if k != 'updated'} == doc:
        return False
    doc = dict(doc, updated=NOW)
    p.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')))
    return True

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ids = json.load(open(IDS))
    cards = {c['slug']: c for c in json.load(open(ROOT / 'data/cards.json'))['cards'] if c['kind'] == 'sports'}
    if '--resolve' in sys.argv:
        for slug, e in ids.items():
            if isinstance(e, dict) and e.get('status') == 'pending':
                resolve(e)
        json.dump(ids, open(IDS, 'w'), indent=1, ensure_ascii=False)
    cache, changed, failed = {}, 0, []
    for slug in cards:
        e = ids.get(slug) or {'status': 'unmatched', 'reason': 'not-mapped'}
        base = {'slug': slug, 'card': cards[slug]['name']}
        if e.get('status') != 'matched':
            doc = dict(base, status='unavailable', reason=e.get('reason', 'not-mapped'), person=e.get('person'))
            changed += write(slug, doc); continue
        key = (e['league'], e['id'])
        if key not in cache:
            try:
                cache[key] = fetch(e)
            except Exception as ex:  # keep previous file on transient failure
                print('FAIL', slug, key, ex, file=sys.stderr); cache[key] = 'ERR'
        data = cache[key]
        if data == 'ERR':
            failed.append(slug); continue
        if not data:
            doc = dict(base, status='unavailable', reason='no-stats-yet', person=e.get('person'),
                       league=LEAGUE_LABEL.get(e['league']))
        else:
            doc = dict(base, status='ok', league=LEAGUE_LABEL.get(e['league']), **data)
            doc['player']['name'] = doc['player'].get('name') or e.get('person')
        changed += write(slug, doc)
    meta = {'lastRun': NOW, 'cards': len(cards), 'players': len(cache), 'failed': failed}
    (OUT / '_meta.json').write_text(json.dumps(meta))
    print(f'{len(cards)} sports cards, {len(cache)} players fetched, {changed} files changed, {len(failed)} failed')
    return 1 if len(failed) > len(cards) // 2 else 0

if __name__ == '__main__':
    sys.exit(main())
