#!/usr/bin/env python3
"""Local preview that mimics GitHub Pages: /foo -> foo.html, /dir/ -> dir/index.html, else 404.html (status 404)."""
import http.server, os, sys, pathlib
DOCS = pathlib.Path(__file__).resolve().parent.parent / 'docs'
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(s, *a, **k): super().__init__(*a, directory=str(DOCS), **k)
    def send_head(s):
        path = s.path.split('?', 1)[0].split('#', 1)[0]
        fs = DOCS / path.lstrip('/')
        if path.endswith('/') and (fs / 'index.html').is_file(): pass
        elif fs.is_file(): pass
        elif (DOCS / (path.lstrip('/') + '.html')).is_file():
            s.path = path + '.html'
        else:
            body = (DOCS / '404.html').read_bytes()
            s.send_response(404); s.send_header('Content-Type', 'text/html; charset=utf-8')
            s.send_header('Content-Length', str(len(body))); s.end_headers()
            import io; return io.BytesIO(body)
        return super().send_head()
    def log_message(s, *a): pass
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
http.server.ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()
