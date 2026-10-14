# DOMjudge Builder - 題目發想平台與 AI 協同架構設計 (AI Ideation & Platform Spec)

本文檔記錄將 `domjudge_builder` 擴展為完整出題生態系的架構方案：將「題目發想（AI 協同創意）」與「工程落實（管線編譯與打包）」深度整合，並確立以 `concept.yaml` 作為系統單一真實來源 (SSOT) 的設計標準。

---

## 一、 核心設計哲學：發想與工程徹底解耦

一般 AI 出題工具常試圖讓 LLM 一次性生成題面、解法、測資與設定，容易導致嚴重的模型幻覺（例如題面要求 $N \le 1000$、測資生成隨機到 $10^5$、解答演算法卻是 $O(N^2)$ 超時）。

本系統採用 **兩階段解耦架構**：
1. **發想期（創意收斂）**：人機對話，專注於演算法思維、情境設計與邊界條件，最終產出結構化的「題目核心概念檔 (`concept.yaml`)」。
2. **工程期（逐步推導與校驗）**：以 `concept.yaml` 為基底，逐步推導生成題面、正解、測試資料，並透過本機隔離行程自動校驗。

```
[出題者 + LLM 協同發想]
       │
       ▼ (收斂為結構化規格)
[核心概念檔] problems/<ID>/concept.yaml  <─── (SSOT 單一真實來源)
       │
       ├─────────────────────────────────┐
       ▼                                 ▼
[題面生成] statement.md            [正解與產生器] solver.py
       │                                 │
       ▼ (Edge Headless)                 ▼ (subprocess 隔離執行)
[題本] problem.pdf                 [測試資料] testcases/<ID>/
       │                                 │
       └────────────────┬────────────────┘
                        ▼
             [DOMjudge 封包] dist/<ID>.zip
```

---

## 二、 核心資料格式規格：`concept.yaml`

每道題目均於其獨立目錄 `problems/<ID>/` 中維護一份 `concept.yaml`，作為跨模組編譯的資料基底：

```yaml
id: DBM
title: 製作餅乾後剩下多少材料
difficulty: Easy
tags: [Basic Math, Division, Simulation]
target_course: "DS2027 Midterm"
author: "出題團隊"

# 題目故事與核心演算法概念
concept:
  story_theme: "烘焙餅乾時的材料比例與換算"
  core_algorithm: "整數除法與餘數計算"
  description: "小明烘焙餅乾，每片需固定克數麵粉與牛奶，根據現有材料總量計算最多可做幾片，並輸出剩餘量。"

# 評測時限與記憶體配置 (DOMjudge 標準)
limits:
  timelimit: 1.0
  memory: 64
  float_tolerance: "1E-3"
  samples: 2

# 輸入輸出規格（供 statement.md 與測資產生器共享）
parameters:
  inputs:
    - name: total_milk
      type: float
      range: [1.0, 1000.0]
      description: 現有牛奶總量 (ml)
    - name: req_milk
      type: float
      range: [10.0, 50.0]
      description: 每片餅乾所需牛奶 (ml)
  output:
    format: "整數 count 與浮點數 remain (保留小數點後 2 位)"

# 出題者特別指定的邊界測資清單
edge_cases:
  - "材料剛好為 0"
  - "材料不足以做任何一片餅乾 (輸出 0 與全額剩餘)"
  - "材料剛好整除無剩餘 (remain == 0.0)"
```

---

## 三、 雙視圖 Web 工作台架構 (Dual-View Workbench)

為兼顧出題者的操作體驗與維護成本，系統提供輕量級的雙視圖網頁介面：

### 視圖 A：題目發想協同工作台 (Problem Ideation Co-pilot)
* **API Key 設定**：介面支援直接貼上 LLM API 金鑰（支援 Gemini / OpenAI 等主流模型）。
* **題庫導航與脈絡注入**：
  * 左側列出工作區已存在的題目列表（含標籤、難度）。
  * 支援將既有題目拖入或勾選進對話脈絡（作為 Few-shot 參考，防止題型撞車並維持整場考試的難度曲線）。
* **多輪對話互動**：
  * 出題者提出構想（例如：「我想出一題結合背包問題但限制重量為浮點數的題目，參考 DBM 的輸入風格」）。
  * Agent 透過對話協助補充邊界條件、設定數值範圍。
* **階段產出**：
  * 點擊「儲存題目概念」，僅將成果寫入 `problems/<ID>/concept.yaml`，**此階段不急於產生代碼與題本**。

### 視圖 B：題目工程與管線管理看板 (Problem Pipeline Workbench)
* **管線進度看板**：
  * 集中展示題庫中每道題目的生成進度燈號：
    `[ 概念定義 ] ──► [ 題面 MD/PDF ] ──► [ 解答與測資 ] ──► [ DOMjudge ZIP ]`
* **半自動工作台 (Human-in-the-Loop)**：
  1. **產生與編輯題面**：點擊依據 `concept.yaml` 生成 `statement.md`，內建 Markdown 編輯器供微調，並調用 Edge Headless 即時預覽 PDF。
  2. **產生與校驗解答**：生成 `solver.py`（含 `solver()` 與 `generate_inputs(seed)`）。
  3. **本機隔離測試**：提供「執行驗證」按鈕，後端以 `subprocess` 跑過所有範例與隨機測資，即時回傳執行耗時與輸出結果。
  4. **DOMjudge 參數微調**：微調時限、記憶體限制、`samples` 數量與 `validator_flags`。
  5. **一鍵建置**：確認無誤後，一鍵封裝為符合 DOMjudge 7.3.3 規範的 `<id>.zip`。

---

## 四、 系統架構與技術原則 (Senior Dev Principles)

1. **Python 單一服務驅動（零 Node.js 依賴）**：
   * 拒絕複雜的前後端分離專案配置。使用 Python 原生輕量框架（如 FastAPI + Vanilla JS/CSS 單檔，或 Streamlit）提供服務。
   * 終端機只要執行 `python domjudge_cli.py serve` 即可在瀏覽器開啟，出題人員無需安裝 Node.js 或 npm。
2. **Core Engine 優先（Web 為薄封裝）**：
   * 所有核心能力（`concept.yaml` 讀寫、PDF 編譯、測資執行、ZIP 打包）必須先作為獨立的 CLI 指令與 Python 模組實作。
   * Web 伺服器僅透過標準介面調用底層模組，確保在無圖形介面的 CI/CD 環境下仍能以命令列批次打包。
3. **安全隔離與防呆 (Defensive Execution)**：
   * 正解程式與測資產生必須採用 `subprocess.run(..., timeout=5)` 執行，具備行程隔離與死迴圈強制終止能力。
   * Markdown 的範例輸出與 Solver 輸出在建置時必須自動比對，不一致則報錯中斷。

---

## 五、 實作推進路線圖 (Roadmap)

* [ ] **Phase 1：穩固 Core Engine 與 CLI**
  * `concept.yaml` 與 `statement.md` 雙向解析模組。
  * `subprocess` 測資執行引擎與範例自動比對。
  * DOMjudge 7.3.3 標準打包模組與 CLI 介面（`build`, `preview`）。
* [ ] **Phase 2：LLM 協同產生器 (AI Bridge)**
  * Prompt 模板設計（Concept $\to$ Statement, Concept $\to$ Solver）。
  * 支援配置 API Key 的輕量 LLM 呼叫模組。
* [ ] **Phase 3：雙視圖 Web 工作台**
  * 實作輕量 Web Server 與前端介面（發想協同頁 + 工程管線頁）。
