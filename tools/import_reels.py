#!/usr/bin/env python3
"""Collect living reels (real Grok Imagine videos from the old site) into docs/videos/{slug}.mp4
and write data/reels.json (slug -> reel info), which build.py reads.

  python3 tools/import_reels.py          # copy/verify sources listed below, rewrite data/reels.json

Every source here is a byte-for-byte download of the old app's /videos/{slug}.mp4 (Grok Imagine
output, H.264 High, 24 fps, faststart, no audio). Never add still-image pan/zoom (Ken Burns) videos.
Files above MAX_BYTES are re-encoded with ffmpeg (H.264 CRF 23, faststart); the rest are copied as-is.
"""
import json, pathlib, shutil, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs/videos'
MAX_BYTES = 15 * 1024 * 1024
AD = '/workspace/prizecardvault/ad_assets'               # fetched 2026-09-10 from prizecardvault.com/videos/{slug}.mp4 (see MANIFEST.md)
KS = '/workspace/kickstarter/video/cinematic/assets/native'  # native old-site downloads saved for the Kickstarter cut
SOURCES = {
    'drake-maye-nave':         f'{AD}/drake-maye-nave.mp4',
    'erling-haaland-locker':   f'{AD}/erling-haaland-locker.mp4',
    'jalen-hurts-film':        f'{AD}/jalen-hurts-film.mp4',
    'jamarr-chase-nave':       f'{AD}/jamarr-chase-nave.mp4',
    'josh-allen-oil':          f'{AD}/josh-allen-oil.mp4',
    'lionel-messi-nave':       f'{AD}/lionel-messi-nave.mp4',
    'shohei-ohtani-locker':    f'{AD}/shohei-ohtani-locker.mp4',
    'vj-edgecombe-nave':       f'{AD}/vj-edgecombe-nave.mp4',
    'jalen-hurts-phoenix':     f'{KS}/jalen-hurts-phoenix.mp4',
    'josh-allen-unstoppable':  f'{KS}/josh-allen-unstoppable.mp4',
    'lamar-jackson':           f'{KS}/lamar-jackson.mp4',
    'trevor-lawrence-sunrise': f'{KS}/trevor-lawrence-sunrise.mp4',
    'drake-maye-spray':        f'{KS}/try-drake-maye-spray.mp4',
    'drake-maye':              f'{KS}/try-drake-maye.mp4',
}

def probe(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                        'stream=width,height,codec_name:format=duration', '-of', 'json', str(p)],
                       capture_output=True, text=True, check=True)
    j = json.loads(r.stdout); s = j['streams'][0]
    return s['width'], s['height'], round(float(j['format']['duration']), 2), s['codec_name']

def main():
    slugs = {c['slug'] for c in json.load(open(ROOT / 'data/cards.json'))['cards']}
    OUT.mkdir(parents=True, exist_ok=True)
    # keep reels added by tools/add_reels.py (new Imagine batches); this script only owns SOURCES
    old = json.load(open(ROOT / 'data/reels.json'))['reels'] if (ROOT / 'data/reels.json').exists() else {}
    reels = {k: v for k, v in old.items() if k not in SOURCES and (OUT / f'{k}.mp4').exists()}
    for slug, src in sorted(SOURCES.items()):
        assert slug in slugs, f'unknown slug {slug}'
        dst = OUT / f'{slug}.mp4'
        src = pathlib.Path(src)
        if src.exists():
            if src.stat().st_size > MAX_BYTES:
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-an', '-c:v', 'libx264', '-profile:v', 'high',
                                '-pix_fmt', 'yuv420p', '-crf', '23', '-preset', 'slow', '-vf', "scale='min(1080,iw)':-2",
                                '-movflags', '+faststart', str(dst)], check=True)
            elif not dst.exists() or dst.read_bytes() != src.read_bytes():
                shutil.copy2(src, dst)
        elif not dst.exists():
            print('missing source and output for', slug, file=sys.stderr); continue
        w, h, dur, codec = probe(dst)
        assert codec == 'h264' and dst.stat().st_size < 95 * 1024 * 1024, slug
        reels[slug] = {'src': f'/videos/{slug}.mp4', 'width': w, 'height': h, 'duration': dur,
                       'bytes': dst.stat().st_size, 'from': str(src)}
    for f in OUT.glob('*.mp4'):
        if f.stem not in reels:
            print('note: unmapped file in docs/videos:', f.name, file=sys.stderr)
    json.dump({'_note': 'slug -> living reel (Grok Imagine video). Old-site reels: tools/import_reels.py; '
                        'new Imagine batches: tools/add_reels.py. Read by build.py.',
               'reels': dict(sorted(reels.items()))}, open(ROOT / 'data/reels.json', 'w'), indent=1)
    print(len(reels), 'reels ->', ROOT / 'data/reels.json')

if __name__ == '__main__':
    main()
