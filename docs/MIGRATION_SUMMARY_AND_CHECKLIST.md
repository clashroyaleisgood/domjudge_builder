# 2026 舊版問題診斷、已驗證解法與 2027 重構執行清單 (Migration Summary & Checklist)

> **給下一個對話的無縫接軌指南**：  
> 本文件旨在總結 2026 舊系統的所有痛點、本次討論達成的決策共識與技術實測成果。在開啟新對話重構 `DS2027_domjudge` 時，直接以本文件作為基準即可無痛開工。

---

## 一、 2026 舊版原始問題與架構風險盤點

在原始的 `DS2026_domjudge` 腳本集合中，我們識別出以下核心缺陷：

### 1. 全域單一設定檔覆寫衝突 (Global State Collision)
* **現象**：`file_configs/problem.yaml` 與 `file_configs/domjudge-problem.ini` 是全域單一檔案。每產生一題就會覆寫，且 `domjudge-problem.ini` 甚至只要檔案存在就完全不更新 (`if not exists`)。
* **風險**：批次打包時會發生檔案競態；無法為個別題目獨立設定不同的執行時限 (`timelimit`)、記憶體限制 (`memory`) 或驗證器旗標 (`validator_flags`)。

### 2. 過期測資殘留污染 (Stale Testcase Pollution)
* **現象**：`gen.py` 在寫入 `testcases/<Problem>/` 時未清除目錄內原有檔案。
* **風險**：若題目原本有 10 筆測資，出題者後續修改縮減為 5 筆，舊的 `06` ~ `10` 仍會留在資料夾內，並在打包時被 `os.listdir()` 誤打包進 ZIP，造成比賽出現幽靈測資。

### 3. 測資缺乏隨機種子 (Non-Deterministic / 無法重現)
* **現象**：`solvers/*.py` 的隨機測資生成未指定 `random.seed()`。
* **風險**：每次執行或 import 都會產出不同的測資內容。這會造成 Git 版本控制雜訊不斷，且比賽若出現爭議時出題團隊無法重現當時的那組評測測資。

### 4. 測資生成寫在模組頂層 (Top-Level Import 副作用)
* **現象**：隨機生成迴圈直接寫在檔案頂層。
* **風險**：只要 `import solvers.xxx` 就被迫執行生測資；若亂數碰撞（如 `DED.py` 用 `Faker` 取名重複），更會在頂層觸發 `AssertionError` 直接崩潰。

### 5. 工具鏈割裂與人肉雙重維護
* **現象**：`tool_markdown/` (題目敘述) 與 `main.py` (測資與打包) 完全脫節。
* **風險**：題目 Markdown 寫了一套範例測資，`solvers/*.py` 又手動複製一份，出題者極易改了一邊卻漏了另一邊；且舊版缺乏自動轉 PDF 功能，需手動透過瀏覽器列印並貼到 `file_PDFs/`。

### 6. DOMjudge 規範支援不全
* **現象**：所有測資全數強制丟入 `data/secret/`，完全未支援 `data/sample/`。
* **風險**：參賽者或裁判在 DOMjudge 介面上無法將提交與公開範例測資對齊比對。

### 7. ZIP 已存在時強制報錯崩潰
* **現象**：`pack.py` 檢查 `if exists(dst_path): raise ValueError(...)`。
* **風險**：出題反覆微調時體驗極差，每次都必須手動去資料夾刪除舊 ZIP 才能重新生成。

### 8. 全域 `sys.stdin` 攔截未安全復原
* **現象**：`solvers/base.py` 直接以 `sys.stdin = io.StringIO(...)` 永久覆寫全域標準輸入。
* **風險**：若解答拋出例外中斷，全域 `sys.stdin` 將維持污染狀態，影響後續所有程式。

### 9. 缺乏 CLI 命令列介面
* **現象**：每次出題都必須手動修改 `main.py` 裡面的字串變數。

---

## 二、 本次討論與驗證敲定的核心解法與共識

針對上述問題，我們在 2026 進行了技術實測與修復，並達成以下共識：

### 1. 題面格式：堅持 PDF，採用 Edge Headless 自動轉換
* **決策**：取消將 HTML 作為出題產物給 DOMjudge（因 DOMjudge 題面預覽預設只支援 PDF）。維持以 PDF 作為標準交付產物。
* **技術路線**：**MD $\to$ 臨時 HTML (Jinja2 + MathJax) $\to$ PDF (Microsoft Edge Headless)**。
* **驗證結果**：
  * Windows 內建 Edge (`msedge.exe`) 零額外驅動安裝。
  * 命令列參數：`--headless --disable-gpu --no-sandbox --no-pdf-header-footer --run-all-compositor-stages-before-draw --virtual-time-budget=2000 --print-to-pdf=<abs_path>`。
  * 完美渲染 LaTeX 公式（如 $t, m, 10^6, 14 \div 4 = 3.5$）、灰底等寬程式碼方塊與側邊引用條。

### 2. 排版格式標準化與防斷頁保護
* **模板儲存位置**：`templates/html_template.html`。
* **排版成果**：將題目敘述（題目、輸入、輸出）聚合在第 1 頁；範例測資與限制資訊聚合在第 2 頁，達成精準 2 頁式版面。
* **CSS 防斷頁關鍵**：
  * `@page { size: A4; margin: 15mm 18mm; }`
  * `h1, h3, h4 { break-after: avoid; }` 避免標題落單在頁底。
  * `.sample-group { break-inside: avoid; page-break-inside: avoid; }` 避免範例測資方塊被切在兩頁。
  * `.limit-box { break-inside: avoid; page-break-inside: avoid; }`。

### 3. DOMjudge ZIP 打包規範升級
* **保留 Sample / Secret 彈性**：支援 `num_samples` 參數。`0` 表示全放 secret；`> 0` 則將前 $N$ 筆（如 `01`、`02`）放入 `data/sample/`，其餘放入 `data/secret/`。
* **安全覆寫**：若 ZIP 已存在則自動刪除並重建，不再拋錯中斷。

### 4. 測資清潔與安全隔離
* **舊測資清理**：每次寫入 `testcases/<Problem>/` 前，自動刪除目錄內舊有的 `.in` 與 `.ans`。
* **安全的 contextmanager**：以 Python `contextlib` 實作 `redirect_stdin`，確保例外發生時必定還原 `sys.stdin`。

### 5. 運行環境與前提確認
* **Conda 環境**：統一在 Conda `domjudge` 環境（Python 3.10）執行。
* **聯網保證**：確認出題轉 PDF 時環境一定有網路（MathJax CDN 能順暢載入）。
* **忽略無關目錄**：`0000/` 資料夾為測試殘留物，2027 完全不予使用。

---

## 三、 2027 重構目標與下一步執行清單 (Checklist for Next Chat)

在重開新對話時，請依照下列清單逐步執行 2027 系統的優雅重構：

### 階段一：架構與目錄結構設計 (Architecture Setup)
- [ ] 確定 2027 的目錄組織模式：
  * **推薦方案（以題目為單位封裝）**：
    `problems/<Problem_ID>/` 內包含 `statement.md`、`solver.py`、`config.yaml`。
  * 或維持集中平鋪分類（`markdown/`, `solvers/`, `output/`）。
- [ ] 建立 `templates/` 目錄並放入已驗證的 `html_template.html`。

### 階段二：題目配置宣告化 (Config Decoupling)
- [ ] 徹底消滅全域 `file_configs/`。
- [ ] 改為由題目的 `statement.md` 頂端 YAML Frontmatter 宣告題目名稱、時限與記憶體（或各題專屬 `config.yaml`）：
  ```markdown
  ---
  id: DBM
  name: 製作餅乾後剩下多少材料
  timelimit: 1
  memory: 64
  samples: 2
  validator_flags: 'float_tolerance 1E-3'
  ---
  ```

### 階段三：核心引擎實作 (Core Implementation)
- [ ] `core/markdown_parser.py`：解析 Frontmatter，檢查標題與四大必備章節格式，提取範例輸入輸出。
- [ ] `core/pdf_compiler.py`：調用 Edge Headless 將 Markdown 編譯為高解析 A4 PDF。
- [ ] `core/solver_runner.py`：
  - 封裝為函式 `generate_inputs(seed=42)`，由外層傳入固定 Seed 保證測資可重現。
  - 使用 `redirect_stdin` / `redirect_stdout` 安全執行，加入執行逾時保護（防止出題者寫出死迴圈）。
- [ ] `core/packager.py`：生成獨立的 `problem.yaml`、`domjudge-problem.ini`，並依 `samples` 數量自動分流封裝為 `<id>.zip`。

### 階段四：現代化 CLI 與批次處理 (CLI Interface)
- [ ] 建立 `domjudge_cli.py`：
  - `python domjudge_cli.py build <id>`：建置單題（生 PDF、生測資、打包 ZIP）。
  - `python domjudge_cli.py preview <id>`：僅生成 PDF 供檢視排版。
  - `python domjudge_cli.py build --all`：一鍵批次打包整場考試的所有題目。
