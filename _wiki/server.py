"""agent_playground 위키 뷰어용 로컬 서버.

폴더 맨 위에 있는 .md 파일을 읽어서 브라우저에서 위키처럼 보여 준다.
표준 라이브러리만 사용하고, 내 컴퓨터(127.0.0.1)에서만 접속할 수 있다.
"""

import json
import os
import socket
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

WIKI_DIR = Path(__file__).resolve().parent
BOARD_DIR = WIKI_DIR.parent
DEFAULT_PORT = 8777


def list_pages():
    pages = []
    for p in sorted(BOARD_DIR.glob("*.md"), key=lambda p: p.name.lower()):
        title = p.stem
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        except (OSError, UnicodeDecodeError):
            pass
        stat = p.stat()
        pages.append({"name": p.name, "title": title, "mtime": stat.st_mtime, "size": stat.st_size})
    return pages


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WIKI_DIR), **kwargs)

    def log_message(self, format, *args):
        pass  # 콘솔을 조용하게 유지

    def send_body(self, body, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/api/pages":
            body = json.dumps(list_pages(), ensure_ascii=False).encode("utf-8")
            return self.send_body(body, "application/json; charset=utf-8")
        if path.startswith("/raw/"):
            name = path[len("/raw/"):]
            target = (BOARD_DIR / name).resolve()
            # 폴더 맨 위의 .md 파일만 허용
            if target.parent != BOARD_DIR or target.suffix.lower() != ".md" or not target.is_file():
                return self.send_body("없는 페이지".encode("utf-8"), "text/plain; charset=utf-8", 404)
            return self.send_body(target.read_bytes(), "text/markdown; charset=utf-8")
        return super().do_GET()


def pick_port(preferred):
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    ports = [int(a) for a in sys.argv[1:] if a.isdigit()]
    if os.environ.get("PORT", "").isdigit():
        ports.insert(0, int(os.environ["PORT"]))
    port = pick_port(ports[0] if ports else DEFAULT_PORT)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"위키 뷰어: {url}")
    print("끄려면 이 창에서 Ctrl+C", flush=True)
    if "--no-browser" not in sys.argv:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
