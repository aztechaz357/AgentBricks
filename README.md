# AgentBricks

スキルとエージェントを小さな部品として 1 個ずつ積み上げ、自分の組織を作るためのテンプレート。最初は部品を作るためのスキルしか入っていない。Claude Code と GitHub Copilot の両方で使う。

## 部品は 3 種類だけ

| 部品 | 何か | 置き場所 | 作り方 |
|---|---|---|---|
| スキル | 1 つの作業。手順 (SKILL.md、60 行まで) と、出力の型や観点や知識 (references/) | `.github/skills/<名前>/` | `/new-skill <作業の説明>` |
| エージェント | 役割。スキルを 1〜3 個読む | `.github/agents/<名前>.agent.md` | `/new-agent <役割の説明>` |
| 窓口 | 担当のエージェントに仕事を割り振るスキル | `.github/skills/<名前>/SKILL.md` | `/new-desk <受け付ける仕事>` |

```
窓口 ──割り振る──▶ エージェント ──読む──▶ スキル
```

型は `templates/` にある。手で写して埋めてもよい。

## スキルの中身

```
.github/skills/write-weekly-report/
  SKILL.md              手順だけ (60 行まで)。下の references を「要るときに読む」と指す
  references/
    format.md           出力の型 (見出しの並び、書き方の決まり)
    checklist.md        確かめる観点 (レビュー、バグ探しで使う)
    notes.md            知っておくこと (用語、見る場所、使うコマンド)
    examples/           入力と出力の例
```

references は作業の形に合わせて要るものだけを置く。

| 作業の形 | 例 | 主な references |
|---|---|---|
| 作る | いつもの報告書、外部仕様書 | format、examples |
| 調べる | バグ探し、メモリ配置の調べ方 | notes、checklist、format |
| 確かめる | 資料のレビュー | checklist、format、examples |

見本: [設計書のレビューのスキル](examples/review-design/README.md)。材料、できたスキル、試した結果が並んでいる (架空の資料。読み込まれない場所に置いてある)。

## 始め方

1. このリポジトリを GitHub の「Use this template」で自分用に作る (またはフォルダをコピーする)。
2. スキルにしたい作業の材料を `inbox/<名前>/` に置く。`input/` に入力の例、`output/` に出力の例、`memo.md` にいつもの進め方。レビューなら、レビュー前を `input/`、直した後を `output/` に置く。材料は Git に入らない。
3. チャットで `/new-skill <名前> <作業の説明>`。材料から手順と references を作る。材料がなくても、質問に答えれば作れる。
4. 実際の仕事で `/<名前>` と呼んで使い、手順と references を直す。
5. 慣れたら次の部品を 1 個足す。どこで何を足すかは [積み上げの段階](docs/levels.md)。

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
| スキルの補助ファイル | SKILL.md から指したファイルを、要るときに読む | スキルのフォルダに置いたファイルを使える | `references/` に置き、フォルダごと `.claude/` へ写す |
| エージェントの場所 | `.claude/agents/<名前>.md` | `.github/agents/<名前>.agent.md` | `.github/` に書き、`.claude/` へ変換する |
| エージェントの `tools` | 道具の名前 (`Read, Grep, Glob` など) | 別名 (`read`、`search`、`edit`、`execute`、`web`、`agent`) | 別名で書き、`sync.py` が Claude の名前に直す |
| エージェントに読ませるスキル | `skills` 欄でも指定できる | `skills` 欄でも指定できる | 欄は使わず、本文に `.github/skills/<名前>/SKILL.md` と書いて読ませる (両方で同じに動くため) |

型の記入欄は `〔 〕` で囲んである。残っていると `sync.py` が止める。

## tools/sync.py がすること

- 部品を検査する: 名前とファイル名の一致、説明の有無、型の埋め残し、行数の上限、エージェントが読むスキルが実在するか、SKILL.md が指す references が実在するか。上限はファイルの先頭で変えられる。
- SKILL.md から指されていない references は「注意」として出す (置いても読まれないため)。
- Claude Code 用に `.claude/skills/` (フォルダごと) と `.claude/agents/` を生成する (Copilot は `.github/` をそのまま読む)。
- 組織図 `docs/organization.md` を生成する。どこからも読まれていないスキルも一覧する。
- `python tools/sync.py --check` は書き換えずに調べるだけ (CI 用)。

Python 3.9 以上。追加のライブラリは要らない。

## 確認の状況

- `tools/sync.py` の検査と生成は、試しの部品を置いて確かめた。
- `new-skill` は、架空の設計書レビューの材料で試した。会話を知らないエージェントが手順書だけでスキルを作り、そのスキルで新しい設計書の抜けを拾えた ([見本](examples/review-design/README.md))。実際の仕事の材料ではまだ試していない。
- 生成した部品を Claude Code と GitHub Copilot の画面で実際に呼ぶ確認は、まだしていない (未確認)。
- VS Code は `.claude/agents/` も読むと説明されている。そのため VS Code では同じエージェントが 2 つ並んで見えるかもしれない (未確認)。
