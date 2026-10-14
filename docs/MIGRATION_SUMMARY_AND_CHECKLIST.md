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

## 三、 系統分階段實作計畫與驗收標準 (4-Stage Phased Roadmap)

經討論敲定，全系統依照「**核心閉環先行 $\to$ 命令列封裝 $\to$ AI 協同串接 $\to$ 雙視圖工作台**」4 個階段逐步實作與功能驗收：

### 階段一：Core Engine 最小閉環與 MVP 驗證 (Minimal Core MVP)
* **實作內容**：
  - [ ] 目錄與基準題目建立：建立 `problems/DBM/`，遷移 `statement.md`、`solver.py` 與 `concept.yaml` 作為驗證基準。
  - [ ] `core/spec.py`：規格解析器（雙向寬容：優先讀取 `concept.yaml`；若無則自動 fallback 解析 `statement.md` 的 YAML Frontmatter）。
  - [ ] `core/markdown_engine.py`：解析題面結構、提取 `### 範例輸入 #1` 與 `### 範例輸出 #1`、轉為內部 HTML。
  - [ ] `core/pdf_engine.py`：調用 Edge Headless 將題本渲染為標準 A4 PDF（保留 MathJax 渲染等待預算）。
  - [ ] `core/testcase_runner.py`：
    - 呼叫 `solver.py` 之 `generate_inputs(seed=42)` 產出測試案例。
    - **使用 `subprocess` 進行行程隔離與超時終止**（超時 5s 自動強制 kill，防止死迴圈凍結）。
    - 寫入 `problems/<ID>/testcases/`（每次生成前自動清空舊檔，供人肉抽檢）。
    - **自動交叉檢驗 (Sanity Check)**：將 Markdown 範例輸入餵入 solver，若輸出與題本範例輸出不一致立即報錯中斷。
  - [ ] `core/packager.py`：自動生成個別專屬之 `problem.yaml` 與 `domjudge-problem.ini`，並依 `samples` 數量自動分流封裝為 `dist/<ID>.zip`。
* **驗收標準 (Acceptance Criteria)**：
  - [ ] 執行單一測試腳本，能順利產出 `problems/DBM/problem.pdf`，排版與公式無誤。
  - [ ] `problems/DBM/testcases/` 產出對應 `.in` 與 `.ans` 明文檔。
  - [ ] 刻意修改 `statement.md` 的範例輸出時，系統能主動攔截並報錯（防呆有效）。
  - [ ] 成功生成 `dist/DBM.zip`，解壓縮結構完全符合 DOMjudge 7.3.3 標準。

### 階段二：現代化 CLI 與多題批次處理 (CLI & Batch Processing)
* **實作內容**：
  - [ ] 建立 `domjudge_cli.py`（使用 Python 標準庫 `argparse`，無第三方框架依賴）。
  - [ ] 支援命令：
    - `python domjudge_cli.py build <ID>`：編譯單題（生 PDF、跑測資、打包 ZIP）。
    - `python domjudge_cli.py preview <ID>`：僅渲染 PDF 供排版預覽。
    - `python domjudge_cli.py check <ID>`：僅跑測資與範例防呆校驗。
    - `python domjudge_cli.py build --all`：一鍵批次建置 `problems/` 內所有題目。
* **驗收標準**：
  - [ ] 終端機參數提示清晰，支援單題與批次打包。
  - [ ] 批次打包時印出進度與總結報告。

### 階段三：LLM 協同發想與生成模組 (AI Bridge)
* **實作內容**：
  - [ ] `ai/client.py`：統一 LLM 客戶端（支援設定 API Key、Base URL，相容 Gemini / OpenAI 格式）。
  - [ ] `ai/prompts.py`：少樣本 (Few-shot) Prompt 模板設計（發想收斂 $\to$ `concept.yaml`、`concept.yaml` $\to$ `statement.md` / `solver.py`）。
  - [ ] CLI 擴展：支援 `python domjudge_cli.py generate <ID> "概念提示詞"`。
* **驗收標準**：
  - [ ] 能依提示詞生成合法之 `concept.yaml`。
  - [ ] 能由 `concept.yaml` 自動推導出合規之題面初稿與正解腳本。

### 階段四：雙視圖 Web 工作台 (Dual-View Workbench)
* **實作內容**：
  - [ ] 實作 `web/server.py` 與 `web/static/`（Vanilla JS + 現代 CSS，零 Node.js / npm 依賴）。
  - [ ] 整合指令：`python domjudge_cli.py serve` 一鍵啟動本機服務。
  - [ ] **視圖 A（發想協同）**：支援輸入 API Key、題庫清單脈絡拖曳/勾選注入、多輪對話收斂存為 `concept.yaml`。
  - [ ] **視圖 B（工程管線）**：題目狀態看板、Human-in-the-Loop 線上編輯、本機 `subprocess` 一鍵測試。
* **驗收標準**：
  - [ ] 本機啟動後瀏覽器打開 `localhost:8000` 即可操作。
  - [ ] 完成從發想對話、儲存概念、在線編輯、一鍵測試到下載 ZIP 的全流程。

---

## 四、 核心架構決策紀錄 (Architecture Decision Records)
1. **設定檔優先順序**：採用「雙向寬容」原則。優先讀取 `concept.yaml`；若無則容許從 `statement.md` 的 Frontmatter 讀取，並能反向匯出 `concept.yaml`。
2. **測資明文保留**：保留 `problems/<ID>/testcases/` 目錄，每次建置自動清空重建，以利出題者檢視原始測資。
3. **安全隔離機制**：正解程式執行全面使用 Python `subprocess.run(..., timeout=5)`，原生防禦死迴圈並隔離全域變數狀態。
4. **Web 零額外環境負擔**：前端採純靜態單頁（HTML/CSS/JS），後端由單一 Python 行程驅動，禁止引入 Node.js/npm 建置流程。
