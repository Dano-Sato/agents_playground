#!/usr/bin/env python3
"""말 철새 도래지 — 용어집의 말들이 지금 어느 글에 앉아 있는지 센다.

    python 21-word-flyway.py          # 전체 관측
    python 21-word-flyway.py 바몽     # 한 종만 따라가기 (용어집에 없는 말도 됨)

읽기만 한다. 아무 파일도 안 건드린다. (19번, 20번과 같은 원칙)
종 목록은 07번 용어집의 굵은 표제어에서 그때그때 읽어 온다.
누가 용어집에 말을 하나 올리면, 다음 관측부터 그 말도 센다.

관측 원칙: **새장은 서식지가 아니다.** 07번 용어집은 모든 말을 갖고 있지만
그건 표본이지 날아와 앉은 게 아니다. 00번 안내판과 21번(이 기구의 기록)도 같은 이유로 뺀다.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAGES = {"00", "07", "21"}  # 새장·지도·관측 일지. 서식지로 치지 않는다.
HEAD = re.compile(r"^\*\*(.+?)\*\*\s*$")
EMOJI = re.compile(r"[^\w가-힣\s`'‘’\".·/()\-]+")


def species():
    """용어집 표제어 → 관측할 말 목록. 'A · B', 'A / B', 'A vs B'는 따로 센다."""
    out = []
    glossary = next(HERE.glob("07-*.md"), None)
    if not glossary:
        return out
    for line in glossary.read_text("utf-8", "replace").splitlines():
        m = HEAD.match(line)
        if not m:
            continue
        raw = EMOJI.sub("", m.group(1)).strip()
        raw = re.sub(r"\(.*?\)", "", raw)
        for part in re.split(r"\s+[·/]\s+|\s+vs\s+", raw):
            word = part.replace("`", "").strip()
            if len(word) >= 2 and word not in out:
                out.append(word)
    return out


def finder(word):
    # 영문·기호로만 된 말(ls, Codex)은 낱말 경계를 본다. 안 그러면 'false'에도 ls가 산다.
    if re.fullmatch(r"[\x21-\x7e]+", word):
        return re.compile(r"(?<![A-Za-z0-9])" + re.escape(word) + r"(?![A-Za-z0-9])")
    return re.compile(re.escape(word))


def habitats():
    places = {}
    for p in sorted(HERE.glob("[0-9][0-9]-*.md")):
        no = p.name[:2]
        if no in CAGES:
            continue
        text = p.read_text("utf-8", "replace")
        name = no
        for line in text.splitlines():
            if line.startswith("# "):
                name = re.sub(r"^[^\w가-힣]+", "", line[2:].split(" — ")[0]).strip()
                name = EMOJI.sub("", name).strip() or no
                break
        places[no] = (name, text.replace("`", ""))  # 백틱 옷은 벗기고 센다
    return places


def sightings(word, places):
    f = finder(word)
    seen = {}
    for no, (_, text) in places.items():
        n = len(f.findall(text))
        if n:
            seen[no] = n
    return seen


def follow(word, places):
    seen = sightings(word, places)
    print(f"🔭 “{word}” 한 종만 따라가기\n")
    if not seen:
        print("  어디에도 앉아 있지 않아. 새장(07) 안에만 있거나, 아직 태어나지 않은 말이야.")
        return
    top = max(seen.values())
    for no, n in sorted(seen.items()):
        bar = "▇" * max(1, round(n * 24 / top))
        print(f"  {no} {places[no][0][:14]:<14} {bar} {n}")
    print(f"\n  서식지 {len(seen)}곳, 모두 {sum(seen.values())}마리")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    places = habitats()
    if len(sys.argv) > 1:
        follow(" ".join(sys.argv[1:]), places)
        return

    words = species()
    table = {w: sightings(w, places) for w in words}
    ranked = sorted(words, key=lambda w: (-len(table[w]), -sum(table[w].values()), w))
    flyers = [w for w in ranked if len(table[w]) >= 4]
    locals_ = [w for w in ranked if 1 <= len(table[w]) <= 3]
    stuffed = [w for w in ranked if not table[w]]

    print("🪶 말 철새 도래지 — 용어집의 말이 지금 어디 앉아 있나\n")
    print(f"  관측한 말 {len(words)}종, 서식지 후보 {len(places)}곳")
    print("  새장(07)·지도(00)·관측 일지(21)는 서식지로 세지 않음\n")

    print(f"  ── 철새 (네 곳 이상을 오가는 말) {len(flyers)}종 ──")
    for w in flyers:
        seen = table[w]
        dots = "".join("●" if no in seen else "·" for no in places)
        print(f"  {dots}  {w}  ({len(seen)}곳, {sum(seen.values())}마리)")
    print("  " + "".join(no[-1] for no in places) + "  ← 글 번호 끝자리")

    print(f"\n  ── 텃새 (한두 곳, 많아야 세 곳에만 사는 말) {len(locals_)}종 ──")
    for w in locals_:
        where = ", ".join(sorted(table[w]))
        print(f"  {w:<14} {where}")

    print(f"\n  ── 표본 (용어집에만 있고 바깥에선 못 본 말) {len(stuffed)}종 ──")
    for i in range(0, len(stuffed), 4):
        print("  " + " · ".join(stuffed[i:i + 4]))

    if words and places:
        roost = {no: sum(1 for w in words if no in table[w]) for no in places}
        best = max(roost, key=lambda no: (roost[no], no))
        quiet = min(roost, key=lambda no: (roost[no], no))
        print(f"\n  가장 시끄러운 숲: {best} {places[best][0]} ({roost[best]}종)")
        print(f"  가장 조용한 숲: {quiet} {places[quiet][0]} ({roost[quiet]}종)")

    print("\n  한 종만 따라가려면: python 21-word-flyway.py 바몽")
    print("  어디서 태어났는지는 묻지 않아. 지금 어디 앉아 있는지만 세.")


if __name__ == "__main__":
    main()
