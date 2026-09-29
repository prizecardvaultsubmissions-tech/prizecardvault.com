#!/usr/bin/env python3
"""Add a batch of Grok Imagine card reels to the site.

  python3 tools/add_reels.py BATCH.tsv [--force] [-j 2] [--no-build] [--dry-run]

BATCH.tsv: one `slug<TAB>/path/to/source.mp4` per line (blank lines and `#` comments ignored;
paths may contain spaces). For each line:
  1. archive the untouched original to /workspace/reels-master/<slug>.mp4 (never committed)
  2. encode the web copy docs/videos/<slug>.mp4 with ffmpeg: H.264 High, yuv420p, no audio
     (the player is muted), long side 960 px (aspect kept, even dims, never upscaled), +faststart.
     CRF is picked per clip so the file lands in the size window (default 2.5-3.2 MB, aim 2.8 MB;
     1 MB = 1,000,000 bytes): start at CRF 26, re-encode with a predicted CRF (size ~ x0.86 per
     CRF step) until in the window, clamped to CRF 20..30 so quality never drops below CRF 30.
  3. verify the output (h264, no audio, duration matches the source within 0.5 s)
  4. record it in data/reels.json (merged; other entries kept), then run build.py once.
Idempotent: a slug whose web copy already exists is skipped unless --force (which re-archives
the original and re-encodes). No poster JPG is made: the full-screen player uses the card's
front image (/cards/<slug>.jpg, already on the site) as the poster.
Budget: GitHub Pages publishes docs/ (limit 1 GB); every committed video also stays in git
history, so re-encoding (--force) a committed reel costs its size again in the repo.
"""
import argparse, json, math, os, pathlib, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs/videos'
MASTER = pathlib.Path('/workspace/reels-master')
REELS_JSON = ROOT / 'data/reels.json'
LONG_SIDE = 960
MB = 1_000_000
CRF_START, CRF_MIN, CRF_MAX = 26.0, 20.0, 30.0
STEP_RATIO = 0.86          # measured on batch 1: each +1 CRF ~ x0.86 file size
PAGES_LIMIT = 1_000_000_000


def probe(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                        'stream=index,codec_type,codec_name,width,height,disposition:format=duration',
                        '-of', 'json', str(p)], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f'ffprobe failed on {p}: {r.stderr.strip()}')
    j = json.loads(r.stdout)
    vids = [s for s in j['streams'] if s['codec_type'] == 'video'
            and not s.get('disposition', {}).get('attached_pic')]
    auds = [s for s in j['streams'] if s['codec_type'] == 'audio']
    if not vids:
        raise RuntimeError(f'no video stream in {p}')
    v = vids[0]
    return {'index': v['index'], 'width': v['width'], 'height': v['height'], 'codec': v['codec_name'],
            'duration': float(j['format']['duration']), 'audio': bool(auds)}


def scale_dims(w, h):
    long_ = max(w, h); target = min(LONG_SIDE, long_ - long_ % 2)
    even = lambda x: max(2, int(round(x / 2)) * 2)
    return (target, even(h * target / w)) if w >= h else (even(w * target / h), target)


def encode(src, vindex, w, h, crf, dst):
    cmd = ['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', str(src), '-map', f'0:{vindex}',
           '-an', '-sn', '-dn', '-map_metadata', '-1', '-map_chapters', '-1',
           '-vf', f'scale={w}:{h}:flags=lanczos,setsar=1', '-c:v', 'libx264', '-preset', 'slow',
           '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-crf', f'{crf:g}', '-threads', '4',
           '-movflags', '+faststart', '-f', 'mp4', str(dst)]
    subprocess.run(cmd, check=True)
    return dst.stat().st_size


def pick_crf(src, info, lo, hi, aim, log):
    w, h = scale_dims(info['width'], info['height'])
    tried = {}
    crf = CRF_START
    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix='pcv-reel-'))
    try:
        for _ in range(5):
            f = tmpdir / f'crf{crf:g}.mp4'
            size = encode(src, info['index'], w, h, crf, f)
            tried[crf] = (size, f)
            log(f'    crf {crf:g}: {size / MB:.2f} MB')
            if lo <= size <= hi or (size > hi and crf >= CRF_MAX) or (size < lo and crf <= CRF_MIN):
                break
            nxt = crf + math.log(size / aim) / math.log(1 / STEP_RATIO)
            nxt = min(CRF_MAX, max(CRF_MIN, round(nxt * 2) / 2))
            if nxt in tried:
                break
            crf = nxt
        inwin = [c for c, (s, _) in tried.items() if lo <= s <= hi]
        if inwin:
            best = min(inwin, key=lambda c: abs(tried[c][0] - aim))
        else:  # closest to the window (prefer the one at/under hi)
            under = [c for c, (s, _) in tried.items() if s <= hi]
            best = max(under, key=lambda c: tried[c][0]) if under else min(tried, key=lambda c: tried[c][0])
        return best, w, h, tried[best][1], tmpdir
    except BaseException:
        shutil.rmtree(tmpdir, ignore_errors=True); raise


def process(slug, src, a, cards):
    lines = []
    log = lines.append
    dst = OUT / f'{slug}.mp4'
    master = MASTER / f'{slug}.mp4'
    try:
        if slug not in cards:
            raise RuntimeError('unknown slug (not in data/cards.json)')
        if dst.exists() and not a.force:
            if not master.exists() and src.exists():
                shutil.copy2(src, master); log(f'  archived original -> {master}')
            return slug, 'skip', None, lines
        if not src.exists():
            raise RuntimeError(f'source not found: {src}')
        info = probe(src)
        if a.dry_run:
            log(f'  would encode {info["width"]}x{info["height"]} {info["duration"]:.2f}s -> {scale_dims(info["width"], info["height"])}')
            return slug, 'dry', None, lines
        # 1. archive the original (byte copy; overwritten only with --force)
        if not master.exists() or (a.force and not same_file(src, master)):
            tmp = master.with_suffix('.mp4.part'); shutil.copy2(src, tmp); os.replace(tmp, master)
            log(f'  archived original -> {master} ({master.stat().st_size / MB:.1f} MB)')
        # 2. encode from the archived master
        crf, w, h, f, tmpdir = pick_crf(master, info, a.min_mb * MB, a.max_mb * MB, a.aim_mb * MB, log)
        try:
            out = probe(f)
            if out['codec'] != 'h264' or out['audio'] or abs(out['duration'] - info['duration']) > 0.5 \
                    or (out['width'], out['height']) != (w, h):
                raise RuntimeError(f'output check failed: {out}')
            tmp = dst.with_suffix('.mp4.part'); shutil.copyfile(f, tmp); os.replace(tmp, dst)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        size = dst.stat().st_size
        entry = {'src': f'/videos/{slug}.mp4', 'width': w, 'height': h, 'duration': round(out['duration'], 2),
                 'bytes': size, 'from': str(master), 'source': 'Grok Imagine', 'crf': crf,
                 'master': {'width': info['width'], 'height': info['height'], 'bytes': master.stat().st_size,
                            'file': src.name}}
        log(f'  -> {dst.relative_to(ROOT)} {w}x{h} crf {crf:g} {size / MB:.2f} MB {out["duration"]:.2f}s')
        return slug, 'ok', entry, lines
    except Exception as ex:
        log(f'  ERROR: {ex}')
        return slug, 'error', None, lines


def same_file(a, b):
    if a.stat().st_size != b.stat().st_size:
        return False
    with open(a, 'rb') as x, open(b, 'rb') as y:
        while True:
            p, q = x.read(1 << 20), y.read(1 << 20)
            if p != q: return False
            if not p: return True


def read_tsv(path):
    rows, seen = [], set()
    for n, line in enumerate(open(path, encoding='utf-8'), 1):
        line = line.rstrip('\r\n')
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if '\t' not in line:
            sys.exit(f'{path}:{n}: expected slug<TAB>path')
        slug, src = (x.strip() for x in line.split('\t', 1))
        if slug in seen:
            sys.exit(f'{path}:{n}: duplicate slug {slug}')
        seen.add(slug)
        rows.append((slug, pathlib.Path(os.path.expanduser(src))))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('tsv')
    ap.add_argument('--force', action='store_true', help='re-archive + re-encode slugs that already have a web copy')
    ap.add_argument('-j', '--jobs', type=int, default=2, help='parallel encodes (default 2)')
    ap.add_argument('--min-mb', type=float, default=2.5)
    ap.add_argument('--max-mb', type=float, default=3.2)
    ap.add_argument('--aim-mb', type=float, default=2.8)
    ap.add_argument('--no-build', action='store_true', help='do not run build.py afterwards')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)
    for tool in ('ffmpeg', 'ffprobe'):
        if not shutil.which(tool): sys.exit(f'{tool} not found')
    rows = read_tsv(a.tsv)
    cards = {c['slug'] for c in json.load(open(ROOT / 'data/cards.json'))['cards']}
    OUT.mkdir(parents=True, exist_ok=True); MASTER.mkdir(parents=True, exist_ok=True)
    print(f'{len(rows)} reels in {a.tsv}')
    results = []
    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        for slug, status, entry, lines in ex.map(lambda r: process(r[0], r[1], a, cards), rows):
            print(f'{slug}: {status}'); [print(l) for l in lines]
            results.append((slug, status, entry))
    new = {s: e for s, st, e in results if st == 'ok'}
    if new:
        data = json.load(open(REELS_JSON))
        data['reels'].update(new)
        data['reels'] = dict(sorted(data['reels'].items()))
        data['_note'] = ('slug -> living reel (Grok Imagine video). Old-site reels: tools/import_reels.py; '
                         'new Imagine batches: tools/add_reels.py. Read by build.py.')
        tmp = REELS_JSON.with_suffix('.json.part')
        with open(tmp, 'w') as fh:
            json.dump(data, fh, indent=1)
        os.replace(tmp, REELS_JSON)
    counts = {k: sum(1 for _, s, _ in results if s == k) for k in ('ok', 'skip', 'error', 'dry')}
    print('summary:', ', '.join(f'{k} {v}' for k, v in counts.items() if v))
    total = sum(f.stat().st_size for f in OUT.glob('*.mp4'))
    n = len(list(OUT.glob('*.mp4')))
    site = sum(f.stat().st_size for f in (ROOT / 'docs').rglob('*') if f.is_file())
    print(f'docs/videos: {n} files, {total / MB:.1f} MB; docs/ total {site / MB:.1f} MB '
          f'({site / PAGES_LIMIT:.0%} of the 1 GB Pages limit)')
    if new and not a.no_build and not a.dry_run:
        subprocess.run([sys.executable, str(ROOT / 'build.py')], check=True, cwd=ROOT)
    if counts['error']:
        sys.exit(1)


if __name__ == '__main__':
    main()
