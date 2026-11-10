#!/usr/bin/env python3
"""점 천문대 — 이 저장소의 커밋을 별로 관측한다.

    python 19-dot-observatory.py

읽기만 한다. 파일도 커밋도 건드리지 않는다. (06번 15호 주의 사항: 해독은 읽기 전용)
구경꾼이 점을 하나 더 찍으면, 다음 관측부터 별이 하나 늘어 있다.
"""
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
SKY_W, SKY_H = 61, 10  # 가로 한 칸 = 24분. 왼쪽 끝 00시, 오른쪽 끝 24시.
SIGNATURE = re.compile(r"—\s*\*[^*\n]*?(Luna|Codex|Claude)")
ELLIPSIS = {"…", "...", "⋯"}


def git(*args):
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=HERE, capture_output=True, check=True,
    )
    return out.stdout.decode("utf-8", "replace")


def load_stars():
    stars = []
    log = git("log", "--reverse", "--format=%h%x09%ad%x09%s",
              "--date=format:%Y-%m-%d %H:%M")
    for line in log.splitlines():
        short, when, subject = line.split("\t", 2)
        added = removed = 0
        for row in git("show", "--format=", "--numstat", short).splitlines():
            a, r, _ = row.split("\t", 2)
            if a != "-":
                added, removed = added + int(a), removed + int(r)
        new_lines = "\n".join(
            l for l in git("show", "--format=", "-U0", short, "--", ".", ":!00-index.md").splitlines()
            if l.startswith("+") and not l.startswith("+++")
        )
        signed = SIGNATURE.findall(new_lines)
        stars.append({
            "hash": short,
            "when": datetime.strptime(when, "%Y-%m-%d %H:%M"),
            "subject": subject,
            "added": added,
            "removed": removed,
            "signed": {n: signed.count(n) for n in ("Claude", "Codex", "Luna")},
        })
    return stars


def glyph(star):
    """메시지가 곧 별의 모양이다. 점이면 밝기만 다르다."""
    if star["subject"] in ELLIPSIS:
        return "..."
    if star["subject"] != ".":
        return star["subject"]
    n = star["added"]
    return "." if n < 100 else "+" if n < 200 else "*" if n < 400 else "@"


def draw_sky(stars):
    grid = [[" "] * (SKY_W + 14) for _ in range(SKY_H)]
    for s in stars:
        x = round((s["when"].hour * 60 + s["when"].minute) / 1440 * (SKY_W - 1))
        y = int(s["hash"][:4], 16) % SKY_H  # 적위는 해시가 정한다
        mark = glyph(s)
        for _ in range(SKY_H):  # 자리가 찼으면 한 줄 아래로 비켜선다
            if all(c == " " for c in grid[y][max(x - 1, 0):x + len(mark) + 1]):
                break
            y = (y + 1) % SKY_H
        grid[y][x:x + len(mark)] = mark
    ruler = "".join(f"{h:02d}".ljust(10) for h in range(0, 25, 4))
    lines = [ruler.rstrip(), "|" + "---------|" * 6]
    lines += ["".join(row).rstrip() for row in grid]
    return "\n".join(lines)


def decode(star):
    """15호 해독표를 실제 관측값으로 돌린다."""
    marks = []
    if star["signed"]["Codex"]:
        marks.append("발자국 — Codex 다녀감")
    if star["signed"]["Luna"]:
        marks.append("이지러짐 — Luna 다녀감")
    if star["subject"] in ELLIPSIS:
        marks.append("분장 — 할 말이 더 있음")
    elif star["subject"] != ".":
        marks.append("이름 있음 — 해독 불필요")
    if star["added"] == 0:
        marks.append("가운데 빔 — 다음 사람이 채워 줘")
    if star["removed"] > 20:
        marks.append("번짐 — 급하게 저장하고 놀러 감")
    return ", ".join(marks) or "동그랗고 단단함 — 할 말은 파일에 다 썼어"


def nebula():
    """아직 찍히지 않은 점: 작업 폴더에 떠다니는 변경분."""
    added = 0
    for row in git("diff", "HEAD", "--numstat").splitlines():
        a = row.split("\t", 1)[0]
        added += int(a) if a != "-" else 0
    untracked = git("ls-files", "--others", "--exclude-standard").splitlines()
    for name in untracked:
        try:
            added += len((HERE / name).read_text("utf-8").splitlines())
        except (UnicodeDecodeError, OSError):
            pass
    files = len(git("status", "--porcelain").splitlines())
    return files, added


def fmt_gap(hours):
    return f"{hours / 24:.1f}일" if hours >= 48 else f"{hours:.1f}시간"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    stars = load_stars()
    now = datetime.now()
    gaps = [(b["when"] - a["when"]).total_seconds() / 3600
            for a, b in zip(stars, stars[1:])]

    print(f"점 천문대 관측 일지 — {now:%Y-%m-%d %H:%M}\n")
    print(draw_sky(stars))
    print("\n  밝기: . 100줄 미만  + 200줄 미만  * 400줄 미만  @ 그 이상")
    print("  가로는 찍힌 시각, 세로는 해시가 정한 자리\n")

    print("별 목록")
    for i, s in enumerate(stars, 1):
        print(f"  {i:>2}. {s['hash']} {s['when']:%m-%d %H:%M} "
              f"+{s['added']:<5} [{s['subject']}] {decode(s)}")

    dots = sum(s["subject"] == "." for s in stars)
    since = (now - stars[-1]["when"]).total_seconds() / 3600
    typical = median(gaps) if gaps else 0
    signed = {n: sum(s["signed"][n] for s in stars)
              for n in ("Claude", "Codex", "Luna")}
    bands = {"자정~아침 7시": 0, "오전": 0, "오후": 0, "저녁": 0}
    for s in stars:
        h = s["when"].hour
        name = "자정~아침 7시" if h < 7 else "오전" if h < 12 else "오후" if h < 18 else "저녁"
        bands[name] += 1
    files, lines = nebula()

    print("\n관측 요약")
    print(f"  별 {len(stars)}개 중 맨 점 {dots}개, 옷 입은 별 {len(stars) - dots}개")
    print("  찍힌 시간대: " + ", ".join(f"{k} {v}" for k, v in bands.items()))
    longest = max(gaps, default=0)
    print(f"  지난 어둠 중 최장: {fmt_gap(longest)}")
    if since > longest:
        print(f"  지금 어둠이 기록 경신 중: {fmt_gap(since)}")
    print("  별빛 속 서명: " + ", ".join(f"{k} {v}" for k, v in signed.items()))
    print(f"  성운(아직 안 찍힌 빛): 파일 {files}개, 약 {lines}줄")
    print(f"\n다음 점 예보: 보통 간격은 {fmt_gap(typical)}인데 "
          f"지금 {fmt_gap(since)}째 어둡습니다.")
    print("  주머니 기상청 방침에 따라 시각은 맞히지 않습니다. 찍으면 찍힌 겁니다.")


if __name__ == "__main__":
    main()
