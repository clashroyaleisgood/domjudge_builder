# 2027 DOMjudge 出題系統重構藍圖 (Refactoring Blueprint)

本文檔針對 2026 版本發現的系統瓶頸、架構債務進行深度剖析，並為 `DS2027_domjudge` 的全新架構提供清晰的設計藍圖與重構建議。

---

## 一、 2026 舊版系統痛點與架構債務回顧

| 模組 / 領域 | 2026 舊版問題 | 潛在風險與後果 | 2027 重構解決方案 |
| :--- | :--- | :--- | :--- |
| **設定檔管理** | `file_configs/problem.yaml` 與 `domjudge-problem.ini` 為全域單一檔案 | 每題打包會互相覆蓋；批次打包時設定檔會發生衝突；無法為個別題目設定不同時限與記憶體 | **題目配置獨立化**：每題獨立設定檔，或直接在 Markdown 開頭以 YAML Frontmatter 定義 |
| **測資確定性** | 隨機測資無固定 `random.seed` | 每次執行或 import 都會生成不同測資；Git 出現大量無意義 churn；比賽出現爭議時無法重現評測測資 | **強制設定 Seed**：以題目代號的 Hash 或顯式 Seed 初始化亂數產生器 |
| **模組匯入副作用** | 測資生成迴圈直接寫在 `solvers/*.py` 模組頂層 (Top-level) | 單純 `import` 就強制執行生測資；若亂數碰撞（如 `Faker` 同名）會在匯入時直接崩潰 | **函式封裝**：將測資生成抽成 `generate_inputs()` 函式，由主程式按需呼叫 |
| **資料雙重維護** | Markdown 中的「範例輸入輸出」與 `solvers/*.py` 中的手工測資各自為政 | 出題者改了 Markdown 題本卻忘了改 solver，兩者內容不一致 | **單一資料來源 (SSOT)**：由系統自動從 Markdown 解析出範例測資直接灌入作為前幾筆測資 |
| **命令列介面** | 舊版 `main.py` 需手動修改程式碼中的題目變數 | 操作繁瑣易出錯，無法支援 CI/CD 或批次打包 | **現代化 CLI**：改為 `argparse` 或 `click` 支援 `build <id>`、`build --all` |
| **死迴圈防護** | 執行 `solver` 時缺乏逾時 (Timeout) 機制 | 若出題者的正解程式寫入死迴圈，打包程序將無限期凍結 | **行程保護**：加入執行逾時限制（如 5 秒），超時主動拋出警告 |

---

## 二、 新版架構設計 (Proposed Architecture)

### 1. 模組化職責分工 (Layered Architecture)
全系統遵循「**Core-first、自包含題目庫、零 Node.js 依賴**」原則：

```
domjudge_builder/
├── domjudge_cli.py              # CLI 命令列進入點 (標準庫 argparse)
│
├── core/                        # [Phase 1] 核心引擎 (零外部框架依賴)
│   ├── __init__.py
│   ├── spec.py                  # concept.yaml 與 Frontmatter 解析 (支援雙向寬容)
│   ├── markdown_engine.py       # Markdown 格式驗證、HTML 轉換與範例提取
│   ├── pdf_engine.py            # HTML 模板渲染與 Edge Headless PDF 生成
│   ├── testcase_runner.py       # subprocess 隔離執行 Solver、5s 逾時防護、範例交叉驗證
│   └── packager.py              # 依 DOMjudge 7.3.3 標準封裝 ZIP (含 sample/secret 分流)
│
├── templates/                   # 排版模板 (HTML / CSS)
│   ├── html_template.html       # 2026 已驗證的 A4 印刷樣式模板
│   └── concept_template.yaml    # 空白概念規格骨架
│
├── problems/                    # [核心資產] 自包含題目庫
│   ├── DBM/
│   │   ├── concept.yaml         # 核心概念 Spec (SSOT)
│   │   ├── statement.md         # 題目敘述
│   │   ├── solver.py            # 解答與 generate_inputs(seed) 函式
│   │   ├── problem.pdf          # [編譯產出] 題本
│   │   └── testcases/           # [編譯產出] 明文測資 (.in / .ans，每次建置重建)
│   └── DAL/
│       ├── concept.yaml
│       ├── statement.md
│       └── solver.py
│
├── dist/                        # 最終生成的 DOMjudge 題目包
│   └── DBM.zip
│
├── ai/                          # [Phase 2] LLM 協同橋接模組 (延遲載入)
│   ├── client.py                # 統一 LLM API Client (Gemini / OpenAI)
│   └── prompts.py               # 發想收斂、題面生成、解答生成模板
│
└── web/                         # [Phase 3] 雙視圖工作台 (零 npm 依賴)
    ├── server.py                # 輕量 FastAPI 後端 (由 domjudge_cli serve 啟動)
    └── static/                  # Vanilla JS + 現代 CSS 單頁應用 (發想頁 + 管線頁)
```

---

## 三、 核心實作升級範例

### 1. 題目 Frontmatter 整合 (消除全域設定檔)
在 `statement.md` 頂部直接宣告題目元數據：
```markdown
---
id: DBM
name: 製作餅乾後剩下多少材料
timelimit: 1
memory: 64
validator_flags: 'float_tolerance 1E-3'
samples: 2
---

### 題目敘述
...
```
系統解析此 Frontmatter 後：
1. 自動生成該題專屬的 `problem.yaml` 與 `domjudge-problem.ini`。
2. 自動知道 `num_samples = 2`，打包時自動將前 2 筆放進 `data/sample/`。

### 2. 確定性測資生成函式規範 (`solver.py`)
```python
import random

def solver():
    # 標準解題邏輯
    pass

def generate_inputs(seed=42) -> list[str]:
    """接受隨機種子，回傳所有測試資料的字串清單"""
    random.seed(seed)
    inputs = []
    # 隨機產生測試案例...
    return inputs
```

### 3. 一鍵批次建置指令設計
```bash
# 建置單題
python domjudge_cli.py build DBM

# 僅產生 PDF 預覽題本
python domjudge_cli.py preview DBM

# 一鍵批次建置整場比賽所有題目包
python domjudge_cli.py build --all
```
