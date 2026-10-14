# DOMjudge Builder

專為程式設計競賽與課程作業打造的現代化 DOMjudge 出題、題本渲染與自動化打包工具。在啟動系統實作前，我們已將既有出題系統的核心資產、技術細節與重構規劃完整歸檔於此。

---

## 核心技術資產與文檔索引

1. **[問題總結、決策共識與重構清單 (新對話首選)](docs/MIGRATION_SUMMARY_AND_CHECKLIST.md)** (`docs/MIGRATION_SUMMARY_AND_CHECKLIST.md`)  
   * **重開新對話的核心入口**：濃縮舊版問題、已驗證通過的解決方案，以及系統重構步驟 Checklist。

2. **[系統架構與規格手冊](docs/SYSTEM_WORKFLOW_AND_SPECS.md)** (`docs/SYSTEM_WORKFLOW_AND_SPECS.md`)
   * **完整的執行管線**：Markdown $\to$ 臨時 HTML $\to$ Edge Headless PDF $\to$ 測資生成 $\to$ DOMjudge ZIP 打包。
   * **題面 Markdown 格式標準**：大標題、四大必要章節、範例組與 LaTeX 數學公式規範。
   * **PDF 列印核心技術細節**：A4 列印 CSS、防斷頁排版保護、Microsoft Edge 命令列參數與等待預算。
   * **DOMjudge 7.3.3 標準壓縮包規範**：`problem.pdf`、`domjudge-problem.ini`、`problem.yaml`、`data/sample/` 與 `data/secret/`。
   * **安全的 I/O 攔截實作**：`contextlib` 標準庫等級的 stdin/stdout 自動還原機制。

3. **[系統重構設計藍圖](docs/REFACTORING_BLUEPRINT.md)** (`docs/REFACTORING_BLUEPRINT.md`)
   * **舊版痛點剖析**：全域設定檔覆寫衝突、測資無種子無法重現、模組頂層匯入副作用、題面範例與測資重複維護。
   * **新版架構規劃**：模組化階層分工、現代化 CLI（支援單題與批次建置）、YAML Frontmatter 整合、確定性測資生成函式。

4. **[印刷樣式 HTML 模板](templates/html_template.html)** (`templates/html_template.html`)
   * 已經過 2026 實測驗證的高解析排版 HTML 模板，內含針對 A4 列印優化的邊距、字級、並排測資框與防斷頁 CSS 規則。

5. **[題目發想平台與 AI 協同架構設計 (新擴展)](docs/AI_IDEATION_AND_PLATFORM_EXPANSION.md)** (`docs/AI_IDEATION_AND_PLATFORM_EXPANSION.md`)
   * **完整的 AI 出題生態規劃**：發想與工程徹底解耦、核心概念規格 (`concept.yaml`)、雙視圖工作台（發想協同頁 vs 工程管線頁）、Human-in-the-Loop 本機校驗機制。

---

## 建議開發環境
本系統依賴於 Conda 環境 `domjudge`：
```powershell
conda activate domjudge
```
* **Python 版本**：3.10+
* **已安裝依賴套件**：`markdown`, `jinja2`, `numpy`, `faker`, `pyyaml`
* **外部引擎**：Windows 內建之 Microsoft Edge (`msedge.exe`)

---

## 快速開始 (Quick Start)

### 1. 啟動雙視圖 Web 工作台 (推薦)
```powershell
python domjudge_cli.py serve
```
* 瀏覽器打開 `http://localhost:8000` 即可使用「題目發想協同」與「工程管線看板」。
* 零 Node.js / npm 依賴，以純 Python 伺服器驅動。

### 2. 常用 CLI 命令列指令
```powershell
# 檢視題目庫現況與生成燈號
python domjudge_cli.py list

# 批次建置所有題目包 (生成 PDF、測資與 ZIP)
python domjudge_cli.py build --all

# 建置單一題目
python domjudge_cli.py build DBM

# 僅渲染題本 PDF 供排版預覽
python domjudge_cli.py preview DBM

# 僅執行格式驗證與 Sanity Check 交叉檢驗
python domjudge_cli.py check DBM

# 使用 AI 協同生成新題目 (以既有題目為參考)
python domjudge_cli.py generate DCA --prompt "小明買披薩要平分給朋友..." --all
```

### 3. 執行全套自動化回歸測試
```powershell
python tests/test_phase1.py  # Core Engine 最小閉環
python tests/test_phase2.py  # CLI 命令列與批次建置
python tests/test_phase3.py  # AI 協同生成模組
python tests/test_phase4.py  # 雙視圖 Web 工作台
```
