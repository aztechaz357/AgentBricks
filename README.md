# AgentBricks

スキルとエージェントを小さな部品として 1 個ずつ積み上げ、自分の組織を作るためのテンプレート。最初は部品を作るためのスキルしか入っていない。Claude Code と GitHub Copilot の両方で使う。

## 部品は 3 種類だけ

| 部品 | 何か | 置き場所 | 作り方 |
|---|---|---|---|
| スキル | 1 つの作業の手順。60 行まで | `.github/skills/<名前>/SKILL.md` | `/new-skill <作業の説明>` |
| エージェント | 役割。スキルを 1〜3 個読む | `.github/agents/<名前>.agent.md` | `/new-agent <役割の説明>` |
| 窓口 | 担当のエージェントに仕事を割り振るスキル | `.github/skills/<名前>/SKILL.md` | `/new-desk <受け付ける仕事>` |

```
窓口 ──割り振る──▶ エージェント ──読む──▶ スキル
```

型は `templates/` にある。手で写して埋めてもよい。

## 始め方

1. このフォルダを自分の作業用にコピーする (または GitHub のテンプレートリポジトリにする)。
2. チャットで `/new-skill <いつもやっている作業の説明>`。スキルが 1 個できる。
3. 実際の仕事で `/<名前>` と呼んで使い、手順を直す。
4. 慣れたら次の部品を 1 個足す。どこで何を足すかは [積み上げの段階](docs/levels.md)。

## 決まり

- 1 回に足す部品は 1 個。使ってみてから次を足す。
- スキルのままで済むなら、エージェントにしない ([エージェントを作る理由](docs/levels.md#エージェントを作る理由))。
- 部品の元は `.github/` だけ。直したら `python tools/sync.py` を実行する。`.claude/` と [組織図](docs/organization.md) が作り直される。
- 足した理由、消した理由は [積み上げの記録](docs/journal.md) に 1 行残す。

## Claude Code と Copilot の書き方の違い

公式の説明 (2026-11-23 に確認) をもとに、両方で読める書き方にそろえている。

| | Claude Code | Copilot (VS Code) | このテンプレートの扱い |
|---|---|---|---|
| スキルの場所 | `.claude/skills/<名前>/SKILL.md` | `.github/skills/<名前>/SKILL.md` | `.github/` に書き、`.claude/` へ写す |
| スキルの中身 | 同じ形式 (`name` と `description`) | 同じ。`name` はフォルダ名と同じ、英小文字・数字・ハイフンで 64 文字まで、`description` は 1024 文字まで | 両方の条件を `sync.py` が検査する |
| エージェントの場所 | `.claude/agents/<名前>.md` | `.github/agents/<名前>.agent.md` | `.github/` に書き、`.claude/` へ変換する |
| エージェントの `tools` | 道具の名前 (`Read, Grep, Glob` など) | 別名 (`read`、`search`、`edit`、`execute`、`web`、`agent`) | 別名で書き、`sync.py` が Claude の名前に直す |
| エージェントに読ませるスキル | `skills` 欄でも指定できる | `skills` 欄でも指定できる | 欄は使わず、本文に `.github/skills/<名前>/SKILL.md` と書いて読ませる (両方で同じに動くため) |

型の記入欄は `〔 〕` で囲んである。残っていると `sync.py` が止める。

## tools/sync.py がすること

- 部品を検査する: 名前とファイル名の一致、説明の有無、型の埋め残し、行数の上限、エージェントが読むスキルが実在するか。上限はファイルの先頭で変えられる。
- Claude Code 用に `.claude/skills/` と `.claude/agents/` を生成する (Copilot は `.github/` をそのまま読む)。
- 組織図 `docs/organization.md` を生成する。どこからも読まれていないスキルも一覧する。
- `python tools/sync.py --check` は書き換えずに調べるだけ (CI 用)。

Python 3.9 以上。追加のライブラリは要らない。

## 確認の状況

- `tools/sync.py` の検査と生成は、試しの部品を置いて確かめた。
- 生成した部品を Claude Code と GitHub Copilot の画面で実際に呼ぶ確認は、まだしていない (未確認)。
- VS Code は `.claude/agents/` も読むと説明されている。そのため VS Code では同じエージェントが 2 つ並んで見えるかもしれない (未確認)。
