#!/usr/bin/env python3
"""Create/refresh data/player-ids.json entries for sports cards (curated subject + league hints).

Each entry: {"person", "league", "status", ...}. status:
  pending    -> update_stats.py --resolve will look up the ID (strict exact-name match, single result)
  matched    -> has "id"; stats are fetched
  unmatched  -> never guessed; Stats tab shows "coming soon" + reason
Existing matched/unmatched entries are never overwritten, so manual fixes stick
(--retry re-queues entries flagged no-confident-match).
"""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent

# Cards whose title isn't the athlete's name (verified from blurbs/slugs).
SUBJECT = {
    'makai-lemon-parallel': 'Makai Lemon', 'jaxon-dart': 'Jaxson Dart',   # card title typo "Jaxon"
    'jalen-hurts-buried': 'Jalen Hurts', 'jalen-hurts-underrated': 'Jalen Hurts',
    'jalen-hurts-underrated-v2': 'Jalen Hurts', 'jalen-hurts-select': 'Jalen Hurts',
    'slim-reaper-classic': 'DeVonta Smith', 'slim-reaper-yokai': 'DeVonta Smith',   # "Slim Reaper", Eagles WR 6
    'slim-reaper-action': 'DeVonta Smith',
    'tyler-shough-saints-rise': 'Tyler Shough', 'trevor-lawrence-tall-order': 'Trevor Lawrence',
    'caleb-williams-franchise': 'Caleb Williams', 'josh-allen-highmark-king': 'Josh Allen',
    'bo-nix-cool-hand': 'Bo Nix',
}
NOT_PLAYER = {  # slug -> reason shown on the tab
    'howie-roseman': 'executive', 'nick-sirianni': 'coach', 'nick-sirianni-peace': 'coach',
    'nick-sirianni-four': 'coach', 'sean-mannion': 'coach', 'vic-fangio': 'coach',
    'vic-fangio-sideline': 'coach', 'vic-fangio-tunnel': 'coach', 'vic-fangio-hoodie': 'coach',
    'no-fly-zone': 'multi-player', 'run-it-back': 'multi-player', 'cosmic-stones': 'multi-player',
    'red-alert': 'multi-player', 'sixers-treasures': 'multi-player', 'eagles-quad': 'multi-player',
    'philadelphia-five': 'multi-player', 'philadelphia-treasures': 'multi-player',
    'mind-tricks': 'unclear-subject',
}
NO_SOURCE = {  # real athletes without a confident free public stats source
    'Sam Gordon': 'No free public stats source for women\'s flag football; ESPN search only returns an unrelated soccer player.',
    'Ellisyn Knapo': 'Not found in ESPN, MLB StatsAPI or other public sources.',
}
LEAGUE = {}
for n in ('A.J. Brown|Amon-Ra St. Brown|Bo Nix|Bobby Wagner|Brock Purdy|Caleb Williams|Cam Skattebo|CeeDee Lamb|'
          'Christian McCaffrey|Cooper DeJean|Dak Prescott|Derrick Henry|Dontayvion Wicks|Drake Maye|Frankie Luvu|'
          'Isaiah Likely|Ja\'Marr Chase|Jalen Carter|Jalen Hurts|James Cook III|Jared Goff|Jaxson Dart|Jaxon Smith-Njigba|'
          'Jayden Daniels|Joe Burrow|Jordan Davis|Jordan Mailata|Josh Allen|Khalil Shakir|Lamar Jackson|Lane Johnson|'
          'Luke McCaffrey|Makai Lemon|Malik Nabers|Matthew Stafford|Micah Parsons|Myles Garrett|Patrick Mahomes|'
          'Patrick Surtain II|Quinyon Mitchell|Riq Woolen|Sam Darnold|Saquon Barkley|Shedeur Sanders|Tank Bigsby|'
          'Travis Kelce|Trevor Lawrence|Tutu Atwell|Ty Simpson|Tyler Shough|Uar Bernard|Will Anderson Jr.|DeVonta Smith').split('|'):
    LEAGUE[n] = 'nfl'
for n in ('Jayson Tatum', 'LeBron James', 'Stephen Curry', 'Tyrese Maxey', 'VJ Edgecombe', 'Victor Wembanyama'):
    LEAGUE[n] = 'nba'
for n in ('Olivia Miles', 'Paige Bueckers', 'Sophie Cunningham'):
    LEAGUE[n] = 'wnba'
for n in ('Bryce Harper', 'Kyle Schwarber', 'Mike Trout', 'Rhys Hoskins', 'Shohei Ohtani', 'Yoshinobu Yamamoto'):
    LEAGUE[n] = 'mlb'
# Disambiguation for common names: only accepted if team + position + jersey all match exactly one
# candidate (jersey numbers come from the card blurbs). Never used to pick between look-alikes otherwise.
HINTS = {
    'Josh Allen': {'team': 'BUF', 'position': 'QB', 'jersey': '17'},
    'Lamar Jackson': {'team': 'BAL', 'position': 'QB', 'jersey': '8'},
    'Jordan Davis': {'team': 'PHI', 'position': 'DT', 'jersey': '90'},
    'DeVonta Smith': {'team': 'PHI', 'position': 'WR', 'jersey': '6'},
}
SEARCH_AS = {'Patrick Surtain II': 'Pat Surtain II'}   # ESPN's listed name
SOCCER = {'Lionel Messi': ['esp.1', 'fra.1', 'usa.1'], 'Erling Haaland': ['aut.1', 'ger.1', 'eng.1']}

def main():
    cards = [c for c in json.load(open(ROOT / 'data/cards.json'))['cards'] if c['kind'] == 'sports']
    p = ROOT / 'data/player-ids.json'
    cur = json.load(open(p)) if p.exists() else {}
    out = {'_doc': 'slug -> player mapping for the Stats tab. Edit by hand; see tools/seed_player_ids.py. '
                   'status: matched | pending | unmatched. league: nfl|nba|wnba|nhl|mlb|soccer|nascar.'}
    for c in cards:
        s = c['slug']
        if s in cur and (cur[s].get('status') == 'matched' or (cur[s].get('status') == 'unmatched'
                         and not ('--retry' in sys.argv and cur[s].get('reason') == 'no-confident-match'))):
            out[s] = cur[s]; continue
        person = SUBJECT.get(s, c['name'])
        if s in NOT_PLAYER:
            out[s] = {'person': None, 'status': 'unmatched', 'reason': NOT_PLAYER[s]}
        elif person in NO_SOURCE:
            out[s] = {'person': person, 'status': 'unmatched', 'reason': 'no-source', 'note': NO_SOURCE[person]}
        elif person in SOCCER:
            out[s] = {'person': person, 'league': 'soccer', 'leagues': SOCCER[person], 'status': 'pending'}
        elif person in LEAGUE:
            out[s] = {'person': person, 'league': LEAGUE[person], 'status': 'pending'}
            if person in HINTS: out[s]['hint'] = HINTS[person]
            if person in SEARCH_AS: out[s]['searchName'] = SEARCH_AS[person]
        else:
            out[s] = {'person': person, 'status': 'unmatched', 'reason': 'unknown-league'}
    json.dump(out, open(p, 'w'), indent=1, ensure_ascii=False)
    print({k: sum(1 for v in out.values() if isinstance(v, dict) and v.get('status') == k) for k in ('pending', 'matched', 'unmatched')})

if __name__ == '__main__':
    main()
