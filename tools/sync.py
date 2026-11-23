"""部品 (`.github/` のスキルとエージェント) を検査し、Claude Code 用のファイルと組織図を生成する。

    python tools/sync.py          検査して生成する
    python tools/sync.py --check  検査と、生成結果が最新かどうかだけを調べる (書き換えない)

元にするのは `.github/skills/<名前>/` (SKILL.md と references/ などのフォルダごと) と
`.github/agents/*.agent.md`。生成するのは `.claude/skills/`、`.claude/agents/`、`docs/organization.md`。
Python 3.9 以上。追加のライブラリは要らない。
"""
import pathlib
import re
import sys

# 小さく保つための上限。自分の組織に合わせて変えてよい
SKILL_MAX_LINES = 60   # スキル 1 個の行数 (SKILL.md)
REF_MAX_LINES = 200    # references などの .md 1 個の行数
TOC_LINES = 100        # これより長い資料には目次を付ける (Anthropic の書き方の指針)
AGENT_MAX_LINES = 25   # エージェント 1 個の行数
AGENT_MAX_SKILLS = 3   # エージェントが読むスキルの数

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC_SKILLS = ROOT / ".github" / "skills"
SRC_AGENTS = ROOT / ".github" / "agents"
DST_SKILLS = ROOT / ".claude" / "skills"
DST_AGENTS = ROOT / ".claude" / "agents"
ORG = ROOT / "docs" / "organization.md"

BUILDERS = {"new-skill", "new-agent", "new-desk"}  # 部品を作るためのスキル。組織図には出さない
TOOLS = {  # Copilot の道具の名前 -> Claude Code の道具の名前
    "read": ["Read"],
    "search": ["Grep", "Glob"],
    "edit": ["Edit", "Write"],
    "execute": ["Bash"],
    "web": ["WebSearch", "WebFetch"],
    "agent": ["Agent"],
}
NOTE = "<!-- tools/sync.py が生成。直接編集せず .github/ 側を直す -->\n"
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PLACEHOLDER = re.compile(r"〔[^〕\n]*〕")  # 型の記入欄の埋め残し (〔名前〕 など)
NAME_MAX = 64  # Copilot のスキル名の上限 (これを超えると読み込まれない)
RESERVED = ("anthropic", "claude")  # スキル名に使わない語 (Anthropic の書き方の指針)
LOCAL_PATH = re.compile(r"`((?:references|scripts|assets)/[^`\s]*)`")  # 資料の中から指しているパス
DESC_MAX = 1024  # Copilot のスキルの説明の上限
SKILL_REF = re.compile(r"\.github/skills/([^/\s`]+)/SKILL\.md")
LOCAL_REF = re.compile(r"`((?:references|scripts|assets)/[^`\s]*)`")  # SKILL.md から指すフォルダの中のファイル


def split(text):
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    return (m.group(1), m.group(2)) if m else (None, text)


def field(front, key):
    m = re.search(rf"^{key}:\s*(.*)$", front, re.M)
    return m.group(1).strip() if m else ""


def load(errors, warnings):
    skills, agents = {}, {}
    for path in sorted(SRC_SKILLS.glob("*/SKILL.md")):
        where = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        front, body = split(text)
        name = path.parent.name
        if front is None:
            errors.append(f"{where}: 先頭の --- で囲んだ部分 (frontmatter) がない")
            continue
        if field(front, "name") != name:
            errors.append(f"{where}: name がフォルダ名 '{name}' と違う")
        if not NAME.match(name) or len(name) > NAME_MAX:
            errors.append(f"{where}: 名前は英小文字、数字、ハイフンで {NAME_MAX} 文字までにする")
        if any(w in name for w in RESERVED):
            errors.append(f"{where}: 名前に {'、'.join(RESERVED)} は使わない")
        if not field(front, "description"):
            errors.append(f"{where}: description が空")
        if len(field(front, "description")) > DESC_MAX:
            errors.append(f"{where}: description が {DESC_MAX} 文字を超えている")
        if len(text.splitlines()) > SKILL_MAX_LINES:
            errors.append(f"{where}: {SKILL_MAX_LINES} 行を超えている。2 個のスキルに分ける")
        if PLACEHOLDER.search(text):
            errors.append(f"{where}: 型の埋め残しがある: {PLACEHOLDER.search(text).group(0)}")
        files = sorted(f.relative_to(path.parent).as_posix() for f in path.parent.rglob("*")
                       if f.is_file() and f != path and "__pycache__" not in f.parts)
        links = list(dict.fromkeys(LOCAL_REF.findall(body)))
        check_files(path.parent, files, links, errors, warnings)
        skills[name] = (front, body, files)
    for path in sorted(SRC_AGENTS.glob("*.agent.md")):
        where = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        front, body = split(text)
        name = path.name[: -len(".agent.md")]
        if front is None:
            errors.append(f"{where}: 先頭の --- で囲んだ部分 (frontmatter) がない")
            continue
        if field(front, "name") != name:
            errors.append(f"{where}: name がファイル名 '{name}' と違う")
        if not NAME.match(name):
            errors.append(f"{where}: 名前は英小文字、数字、ハイフンにする")
        if not field(front, "description"):
            errors.append(f"{where}: description が空")
        if len(text.splitlines()) > AGENT_MAX_LINES:
            errors.append(f"{where}: {AGENT_MAX_LINES} 行を超えている。役割を分ける")
        if PLACEHOLDER.search(text):
            errors.append(f"{where}: 型の埋め残しがある: {PLACEHOLDER.search(text).group(0)}")
        tools = re.findall(r'"([^"]+)"', field(front, "tools"))
        for t in tools:
            if t not in TOOLS:
                errors.append(f"{where}: 道具 '{t}' は使えない。{', '.join(TOOLS)} から選ぶ")
        refs = list(dict.fromkeys(SKILL_REF.findall(body)))
        for r in refs:
            if not (SRC_SKILLS / r / "SKILL.md").is_file():
                errors.append(f"{where}: 読むスキル '{r}' がない。先に new-skill で作る")
        if not refs:
            errors.append(f"{where}: 読むスキルが 1 個もない")
        if len(refs) > AGENT_MAX_SKILLS:
            errors.append(f"{where}: 読むスキルが {AGENT_MAX_SKILLS} 個を超えている。役割を分ける")
        agents[name] = (front, body, tools, refs)
    return skills, agents


def check_files(folder, files, links, errors, warnings):
    """スキルのフォルダの中のファイル (references など) を検査する。"""
    where = folder.relative_to(ROOT).as_posix()
    for link in links:
        if not (folder / link.rstrip("/")).exists():
            errors.append(f"{where}/SKILL.md: 参照している '{link}' がない")
    for f in files:
        try:
            text = (folder / f).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = None  # 画像や Word の様式などは中身を見ない
        if text is not None and PLACEHOLDER.search(text):
            errors.append(f"{where}/{f}: 型の埋め残しがある: {PLACEHOLDER.search(text).group(0)}")
        if text is not None and f.endswith(".md"):
            lines = len(text.splitlines())
            if lines > REF_MAX_LINES:
                errors.append(f"{where}/{f}: {REF_MAX_LINES} 行を超えている。ファイルを分ける")
            if lines > TOC_LINES and not re.search(r"^#+\s*目次", text, re.M):
                warnings.append(f"{where}/{f}: {TOC_LINES} 行を超えている。先頭に「## 目次」を置く")
            for ref in LOCAL_PATH.findall(text):
                if ref.count("/") == 1 and ref.endswith("/"):
                    continue  # 「references/」のようにフォルダの名前を挙げただけのもの
                if ref != f and (folder / ref.rstrip("/")).exists():
                    warnings.append(f"{where}/{f}: 資料から '{ref}' を指している。参照は SKILL.md から 1 段だけにする")
        if not any(f == l or (l.endswith("/") and f.startswith(l)) for l in links):
            warnings.append(f"{where}/{f}: SKILL.md から参照されていない (読まれない)")


def desks(skills, agents):
    """本文にエージェント名をバッククォートで書いているスキルを窓口とみなす。"""
    out = {}
    for name, (_, body, _) in skills.items():
        if name in BUILDERS:
            continue
        members = [a for a in agents if f"`{a}`" in body]
        if members:
            out[name] = members
    return out


def claude_skill(front, body):
    return "---\n" + front + "\n---\n" + NOTE + body


def claude_agent(front, body, tools):
    lines = [f"name: {field(front, 'name')}", f"description: {field(front, 'description')}"]
    if tools:
        lines.append("tools: " + ", ".join(t for a in tools for t in TOOLS[a]))
    return "---\n" + "\n".join(lines) + "\n---\n" + NOTE + body


def first_sentence(front):
    return field(front, "description").split("。")[0]


def organization(skills, agents):
    desk = desks(skills, agents)
    work = [s for s in skills if s not in BUILDERS and s not in desk]
    used = {r for (_, _, _, refs) in agents.values() for r in refs}
    nid = lambda kind, n: kind + "_" + n.replace("-", "_")
    out = [
        "# 組織図",
        "",
        NOTE.strip(),
        "",
        f"窓口 {len(desk)} 個、エージェント {len(agents)} 個、スキル {len(work)} 個 (部品を作るスキルは除く)。",
        "",
    ]
    if not agents and not work:
        out += ["まだ部品はない。`/new-skill` でスキルを 1 個作るところから始める。", ""]
        return "\n".join(out)
    out += ["```mermaid", "flowchart LR"]
    for t in desk:
        out.append(f'    {nid("t", t)}(["{t}"])')
    for a in agents:
        out.append(f'    {nid("a", a)}["{a}"]')
    for s in work:
        out.append(f'    {nid("s", s)}[/"{s}"/]')
    for t, members in desk.items():
        for a in members:
            out.append(f'    {nid("t", t)} --> {nid("a", a)}')
    for a, (_, _, _, refs) in agents.items():
        for r in refs:
            out.append(f'    {nid("a", a)} -.->|読む| {nid("s" if r in work else "t", r)}')
    out += ["```", "", "## 窓口", ""]
    out += [f"- `{t}`: {', '.join(desk[t])}" for t in desk] or ["(まだない)"]
    if agents:
        out += ["", "## エージェント", "", "| エージェント | 役割 | 読むスキル | 道具 |", "|---|---|---|---|"]
    for a, (front, _, tools, refs) in agents.items():
        out.append(f"| `{a}` | {first_sentence(front)} | {', '.join(refs)} | {', '.join(tools) or 'すべて'} |")
    out += ["", "## スキル", "", "| スキル | 何をするか | 参照のファイル | 読むエージェント |", "|---|---|---|---|"]
    for s in work:
        readers = [a for a, (_, _, _, refs) in agents.items() if s in refs]
        front, _, files = skills[s]
        out.append(f"| `{s}` | {first_sentence(front)} | {len(files)} | {', '.join(readers) or '(直接呼ぶだけ)'} |")
    unused = [s for s in work if s not in used]
    if agents and unused:
        out += ["", "## どこからも読まれていないスキル", "", "直接 `/<名前>` で使っていないなら、消すか統合を考える。", ""]
        out += [f"- `{s}`" for s in unused]
    return "\n".join(out) + "\n"


def outputs(skills, agents):
    out = {}
    for name, (front, body, files) in skills.items():
        out[DST_SKILLS / name / "SKILL.md"] = claude_skill(front, body)
        for f in files:
            out[DST_SKILLS / name / f] = (SRC_SKILLS / name / f).read_bytes()
    for name, (front, body, tools, _) in agents.items():
        out[DST_AGENTS / f"{name}.md"] = claude_agent(front, body, tools)
    out[ORG] = organization(skills, agents)
    return out


def generated():
    """以前にこの道具が生成したファイルだけを返す (手で置いたものは消さない)。"""
    made = lambda p: p.is_file() and NOTE in p.read_text(encoding="utf-8")
    out = [p for p in DST_AGENTS.glob("*.md") if made(p)]
    for skill in DST_SKILLS.glob("*/SKILL.md"):
        if made(skill):  # 生成したスキルのフォルダは、中のファイルもすべて生成したもの
            out += [f for f in skill.parent.rglob("*") if f.is_file()]
    return out


def same(path, content):
    if not path.exists():
        return False
    return path.read_bytes() == (content if isinstance(content, bytes) else content.encode("utf-8"))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    check = "--check" in sys.argv
    errors, warnings = [], []
    skills, agents = load(errors, warnings)
    for w in warnings:
        print("注意: " + w)
    if errors:
        print("直すところがある:")
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    out = outputs(skills, agents)
    stale = [p for p in generated() if p not in out]
    changed = [p for p, content in out.items() if not same(p, content)]
    if not check:
        for p in changed:
            p.parent.mkdir(parents=True, exist_ok=True)
            content = out[p]
            if isinstance(content, bytes):
                p.write_bytes(content)
            else:
                p.write_text(content, encoding="utf-8", newline="\n")
        for p in stale:
            p.unlink()
            d = p.parent
            while d not in (DST_SKILLS, DST_AGENTS) and d.exists() and not any(d.iterdir()):
                d.rmdir()
                d = d.parent
    for p in changed + stale:
        verb = ("古い" if check else "更新") if p in changed else ("古い" if check else "削除")
        print(f"{verb}: {p.relative_to(ROOT).as_posix()}")
    print(f"スキル {len(skills)} 個、エージェント {len(agents)} 個を確認した")
    if check and (changed or stale):
        print("python tools/sync.py を実行して生成し直す")
        sys.exit(1)


if __name__ == "__main__":
    main()
