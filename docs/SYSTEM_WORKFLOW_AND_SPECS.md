# DOMjudge 出題系統架構與規格手冊 (System Workflow & Specifications)

本文檔完整記錄 2026 版本經過優化與驗證的出題系統全貌、各模組規格、格式標準與底層技術細節，作為 2027 重構時的核心技術資產與參考標準。

---

## 一、 系統整體架構與管線流程 (Pipeline)

系統的主要職責是將「題目敘述 Markdown」與「解題腳本 Python」自動編譯並打包為符合 **DOMjudge (7.3.3)** 規範的題目壓縮包（ZIP）。

```
[題目敘述] file_MDs/<Problem>.md
      │
      ▼ (Jinja2 + Python-Markdown + MathJax)
[內部臨時 HTML] (A4 印刷樣式 + CSS 防斷頁 + LaTeX 公式)
      │
      ▼ (Microsoft Edge Headless --print-to-pdf)
[題本 PDF] file_PDFs/<Problem>.pdf
      │
      ├─────────────────────────────────────────────┐
      │                                             ▼
[解答與測資] solvers/<Problem>.py             [DOMjudge 題目包打包]
      │                                             │
      ▼ (wrap_both + contextmanager 重導向)         │
[純文字測資] testcases/<Problem>/                   │
      ├─ 01.in / 01.ans                             ▼
      └─ 02.in / 02.ans ... ───────────► file_ZIPs/<Problem>.zip
                                           ├─ problem.pdf
                                           ├─ problem.yaml
                                           ├─ domjudge-problem.ini
                                           └─ data/
                                               ├─ sample/ (可選配)
                                               └─ secret/ (主要測資)
```

---

## 二、 題目 Markdown 格式規範 (Strict Format)

為了確保題本能正確轉為視覺一致、排版工整的 PDF，Markdown 檔案需遵循嚴格結構規範（參考範本 `file_MDs/DAL.md`、`file_MDs/DBM.md`）：

### 1. 文件大標題 (必需)
* 位於第 1 行，格式為 `# <題目代號> - <完整題目名稱>`
* 例如：`# DAL - 製作奶茶還需要多少牛奶`

### 2. 必需章節（順序嚴格固定）
* `### 題目敘述`：詳細題目情境描述。支援條列清單、粗體，若有重點提示可用引言 `> 重點說明` 呈現左側粗條方框。
* `### 輸入說明`：逐行說明輸入參數、資料型態與數學範圍。
* `### 輸出說明`：說明輸出格式與浮點數要求。
* `### 範例輸入 #1` ~ `### 範例輸出 #1`：
  * 編號必須連續從 1 開始。
  * 測資文字需使用 Code Block（三個反引號）包覆。
  * 若有計算說明，可緊接 `### 範例說明 #1`（普通文字或條列式算式）。
* `### 測試資訊`：位於文件最後，定義記憶體與時間限制。
  ```markdown
  ### 測試資訊
  記憶體限制：64MB
  時間限制：1s
  ```

### 3. LaTeX 數學表達式標準
* 行內公式使用單一錢字號 `$expression$`。
* 常用範例：`$t\ (1 \le t \le 1000)$`、`$10^6$`、`$20 \div 4 = 5.0$`、`$3.5 \times 10 = 35.0$`、`$15 - 3 \times 2 = 9.0$`。

---

## 三、 Markdown $\to$ HTML $\to$ PDF 轉換技術細節

### 1. 為什麼採用 MD $\to$ HTML $\to$ PDF？
* **樣式控制力**：Markdown 本身無頁面大小、邊距與左右並排概念。透過 HTML/CSS 能夠最精確地排版並排測資方塊與列印分頁。
* **數學公式品質**：MathJax 3 渲染的數學公式解析度為向量等級，列印成 PDF 清晰無鋸齒。
* **零依賴安裝**：利用 Windows 內建的 Microsoft Edge 核心，免額外下載 Chrome 驅動或數 GB 的 LaTeX 環境。

### 2. HTML 模板與 CSS 印刷規則關鍵設計
模板位於 `templates/html_template.html`：
* **頁面與字級**：
  ```css
  @page {
      size: A4;
      margin: 15mm 18mm; /* 控制邊距使一般題本精準維持在 2 頁內 */
  }
  body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      line-height: 1.5;
      font-size: 15px;
  }
  ```
* **防斷頁保護 (Page Break Avoidance)**：
  ```css
  h1, h3, h4 {
      break-after: avoid; /* 標題絕不落在頁面最後一行而與內容拆開 */
  }
  .sample-group {
      break-inside: avoid;
      page-break-inside: avoid; /* 範例輸入、輸出與說明綁定為同一組，避免被切在兩頁 */
      margin-bottom: 10px;
  }
  .limit-box {
      break-inside: avoid;
      page-break-inside: avoid; /* 測試資訊方塊不跨頁 */
  }
  ```
* **並排灰底測資方塊**：
  ```css
  .sample-row {
      display: flex;
      gap: 20px;
  }
  .sample-box {
      flex: 1;
  }
  pre {
      background: #f5f5f5;
      padding: 8px 10px;
      border-radius: 6px;
      font-family: monospace;
  }
  ```

### 3. Microsoft Edge Headless 列印命令列參數
Python 中透過 `subprocess.run` 執行 Edge 列印：
```python
cmd = [
    edge_executable_path,
    '--headless',
    '--disable-gpu',
    '--no-sandbox',
    '--no-pdf-header-footer',                 # 消除預設的列印網址與日期頁首頁尾
    '--run-all-compositor-stages-before-draw', # 確保樣式與字型載入渲染完成
    '--virtual-time-budget=2000',             # 等候 2 秒確保 MathJax 數學公式繪製完畢
    f'--print-to-pdf={abs_pdf_path}',
    file_url                                  # file:/// 格式的絕對路徑
]
```
* **Edge 執行檔自動搜尋順序**：
  1. `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
  2. `C:\Program Files\Microsoft\Edge\Application\msedge.exe`
  3. `%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe`

---

## 四、 DOMjudge (7.3.3) 題目包 (ZIP) 規範

### 1. 內部目錄結構
```
<problem>.zip
├── problem.pdf               # 由 MD 渲染出的題本 PDF
├── domjudge-problem.ini      # 運行時限配置
├── problem.yaml              # 題目名稱、記憶體、驗證器配置
└── data/
    ├── sample/               # [可選] 公開範例測資 (01.in, 01.ans)
    └── secret/               # 評判隱藏測資 (02.in, 02.ans ...)
```

### 2. 設定檔格式
* **`domjudge-problem.ini`**：
  ```ini
  timelimit='1'
  ```
* **`problem.yaml`**：
  ```yaml
  name: DBM - 製作餅乾後剩下多少材料
  validator_flags: 'float_tolerance 1E-3'
  limits:
      memory: 64
  ```

### 3. Sample 與 Secret 分流機制
* **預設行為 (`num_samples=0`)**：全部測資放入 `data/secret/`。
* **分流行為 (`num_samples=N`)**：檔名序號 $\le N$（例如 `01`、`02`）放入 `data/sample/`，其餘放入 `data/secret/`。

---

## 五、 解答與測資生成機制 (Solvers & Testcases)

### 1. 安全 I/O 攔截工具 (`solvers/base.py`)
出題者的 `solver()` 內部直接撰寫標準 `input()` 與 `print()`。透過 Python 標準庫 contextmanager 達成安全攔截與環境還原：
```python
import sys, io
from contextlib import redirect_stdout, contextmanager

@contextmanager
def redirect_stdin(new_stdin):
    old_stdin = sys.stdin
    sys.stdin = new_stdin
    try:
        yield
    finally:
        sys.stdin = old_stdin  # 確保拋出異常時全域 stdin 必定復原

def wrap_both(solver):
    def new_solver(test_in):
        buf = io.StringIO()
        with redirect_stdin(io.StringIO(test_in)), redirect_stdout(buf):
            solver()
        return buf.getvalue()
    return new_solver
```

### 2. 測資產生策略
* 範例測資：由題目 Markdown 的 `範例輸入` 提取作為前幾筆測資。
* 隨機測資：使用亂數生成大範圍、極端值資料。**（2027 必須加入固定的 `random.seed` 保證可重現性）**。
* 舊測資防污染：每次寫入 `testcases/<Problem>/` 前，必須先遍歷並清除目錄下現有的 `.in` 與 `.ans`，避免過期測資被打包進 ZIP。
