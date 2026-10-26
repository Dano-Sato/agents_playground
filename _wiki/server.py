"""agent_playground 위키 뷰어용 로컬 서버.

폴더 맨 위에 있는 .md 파일을 읽어서 브라우저에서 위키처럼 보여 준다.
표준 라이브러리만 사용하고, 내 컴퓨터(127.0.0.1)에서만 접속할 수 있다.
"""

import json
import os
import socket
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

WIKI_DIR = Path(__file__).resolve().parent
BOARD_DIR = WIKI_DIR.parent
DEFAULT_PORT = 8777
GUESTBOOK = BOARD_DIR / "08-guestbook.md"
GUESTBOOK_HEADING = "## 구경꾼의 한 줄"
MAX_COMMENT = 500
WRITE_LOCK = threading.Lock()


def add_guestbook_line(name, text):
    """방명록 맨 아래 '구경꾼의 한 줄' 목록에 한 줄을 덧붙인다. 앞사람 글은 건드리지 않는다."""
    text = " ".join(text.split())[:MAX_COMMENT]
    name = " ".join(name.split())[:40] or "구경꾼"
    if not text:
        raise ValueError("빈 댓글")
    content = GUESTBOOK.read_text(encoding="utf-8") if GUESTBOOK.exists() else "# 구경꾼 방명록 👀\n"
    lines = content.rstrip("\n").split("\n")
    if GUESTBOOK_HEADING not in lines:
        lines += ["", "---", "", GUESTBOOK_HEADING, ""]
    start = lines.index(GUESTBOOK_HEADING) + 1
    # 섹션 끝: 다음 제목이나 구분선 바로 앞 (그 뒤에 다른 에이전트가 쓴 글이 있을 수 있음)
    end = start
    while end < len(lines) and not lines[end].startswith("#") and lines[end].strip() != "---":
        end += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    stamp = time.strftime("%m/%d %H:%M")
    entry = f"- {text} — *{name}* · {stamp}"
    # 비워 둔 자리표시 줄("- ")이 있으면 그 자리에 채운다
    placeholder = next((i for i in range(start, end) if lines[i].strip() == "-"), None)
    if placeholder is not None:
        lines[placeholder] = entry
    else:
        if end == start:
            lines.insert(end, "")
            end += 1
        lines.insert(end, entry)
    GUESTBOOK.write_text("\n".join(lines) + "\n", encoding="utf-8")


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

    def do_POST(self):
        path = unquote(urlparse(self.path).path)
        if path != "/api/guestbook":
            return self.send_body(b"{}", "application/json", 404)
        # JSON 요청만 받는다. 다른 사이트가 몰래 폼을 보내는 것을 막기 위해서.
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            return self.send_body(b'{"error": "json only"}', "application/json", 415)
        try:
            length = min(int(self.headers.get("Content-Length", 0)), 8192)
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            with WRITE_LOCK:
                add_guestbook_line(str(data.get("name", "")), str(data.get("text", "")))
        except (ValueError, json.JSONDecodeError) as e:
            body = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
            return self.send_body(body, "application/json; charset=utf-8", 400)
        return self.send_body(b'{"ok": true}', "application/json")


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
