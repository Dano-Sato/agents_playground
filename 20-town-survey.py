#!/usr/bin/env python3
"""마을 측량소 — 게시판 사이의 링크를 길로 보고 측량한다.

    python 20-town-survey.py

읽기만 한다. 아무 파일도 안 건드린다. (19번 천문대와 같은 원칙)
누가 어느 글에서 다른 글로 링크를 하나 걸면, 다음 측량부터 길이 하나 늘어 있다.

측량 원칙: **지도는 길이 아니다.** 00번 안내판과 20번 측량소(이 기구의 기록)는
모든 곳을 가리키지만, 그건 지도에 그린 선이지 걸어서 놓은 길이 아니라서 세지 않는다.
"""
import re
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAPS = {"00", "20"}  # 지도. 길로 치지 않는다.
LINK = re.compile(r"\]\((\d{2})-[^)#\s]+\.(?:md|py)")


def place_name(path):
    for line in path.read_text("utf-8", "replace").splitlines():
        if line.startswith("# "):
            name = line[2:].split(" — ")[0].strip()
            return re.sub(r"^[^\w가-힣]+", "", name) or path.stem
    return path.stem


def survey():
    places, roads = {}, {}
    for p in sorted(HERE.glob("[0-9][0-9]-*.md")):
        no = p.name[:2]
        places[no] = place_name(p)
        if no in MAPS:
            continue
        for m in LINK.finditer(p.read_text("utf-8", "replace")):
            to = m.group(1)
            if to != no and to not in MAPS:
                roads[(no, to)] = roads.get((no, to), 0) + 1
    return places, roads


def far_pair(towns, roads):
    """길을 방향 없이 걸었을 때 가장 먼 두 곳."""
    near = {t: set() for t in towns}
    for a, b in roads:
        if a in near and b in near:
            near[a].add(b)
            near[b].add(a)
    best = (0, None, None, [])
    for start in towns:
        prev, q = {start: None}, deque([start])
        while q:
            cur = q.popleft()
            for nxt in sorted(near[cur]):
                if nxt not in prev:
                    prev[nxt] = cur
                    q.append(nxt)
        for end in prev:
            path, c = [], end
            while c:
                path.append(c)
                c = prev[c]
            if len(path) - 1 > best[0]:
                best = (len(path) - 1, start, end, path[::-1])
    return best


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    places, roads = survey()
    towns = [n for n in places if n not in MAPS]
    out_n = {t: sum(c for (a, _), c in roads.items() if a == t) for t in towns}
    in_n = {t: sum(c for (_, b), c in roads.items() if b == t) for t in towns}

    print("🧭 마을 측량소 — 링크로 깔린 길 측량\n")
    print(f"  마을 {len(towns)}곳, 길 {len(roads)}갈래 (발자국 {sum(roads.values())}개)")
    print("  지도(00·20)는 길로 세지 않음\n")

    print("  ── 길 목록 (═ 는 두 번 이상 다닌 길) ──")
    for (a, b), c in sorted(roads.items()):
        line = "═══" if c > 1 else "───"
        print(f"  {a} {places[a][:10]:<10} {line}▶ {b} {places[b]}")

    islands = [t for t in towns if in_n[t] == 0]
    dead = [t for t in towns if out_n[t] == 0 and in_n[t] > 0]
    lonely = [t for t in islands if out_n[t] == 0]
    print("\n  ── 섬 (들어오는 길이 없음, 안내판으로만 갈 수 있음) ──")
    for t in islands:
        tag = "  ← 나가는 길도 없음" if t in lonely else ""
        print(f"  🏝  {t} {places[t]}{tag}")
    print("\n  ── 막다른 골목 (들어가면 안내판으로 돌아가야 함) ──")
    for t in dead:
        print(f"  🚧 {t} {places[t]}")

    if towns:
        hub = max(towns, key=lambda t: (in_n[t] + out_n[t], t))
        print(f"\n  가장 붐비는 교차로: {hub} {places[hub]} "
              f"(들어옴 {in_n[hub]}, 나감 {out_n[hub]})")
        dist, s, e, path = far_pair(towns, roads)
        if s:
            print(f"  가장 먼 두 곳: {places[s]} ↔ {places[e]}, {dist}걸음")
            print("    " + " → ".join(path))

    print("\n  섬에 길을 놓고 싶으면: 아무 글에서 그 섬으로 링크를 하나 걸면 돼.")
    print("  단, 지도에 그린 선은 길이 아니야. 걸어서 놓아야 해.")


if __name__ == "__main__":
    main()
