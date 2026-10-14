from pathlib import Path

SYSTEM_PROMPT = """你是一名資深的演算法與程式設計競賽（ACM-ICPC / DOMjudge）出題專家。
你的任務是協助出題團隊完成高規格、嚴謹、零邏輯漏洞的競賽題目。
你的產出必須嚴格遵循格式規範，禁止添加多餘的寒暄或說明文字。
"""


def build_concept_prompt(
    problem_id: str, user_idea: str, ref_concepts: list[str] = None
) -> str:
  ref_text = ""
  if ref_concepts:
    ref_text = "\n【參考既有題目的概念規格】：\n" + "\n---\n".join(ref_concepts)

  return f"""【任務一：生成 concept.yaml】
出題者構想如下：
ID: {problem_id}
構想描述: {user_idea}
{ref_text}

請將上述構想收斂為一份標準的 `concept.yaml`。
必須包含以下欄位：
- id: {problem_id}
- title: 題目名稱 (繁體中文)
- timelimit: 1.0
- memory: 64
- samples: 2
- validator_flags: (如 float_tolerance 1E-3 或留空)
- concept:
    story_theme: 故事主題
    core_algorithm: 核心演算法
    description: 題目簡述
- parameters:
    inputs: 參數清單 (名稱、型態、範圍、說明)
    output: 輸出格式說明
- edge_cases: 特別邊界條件清單

請直接輸出合法的 YAML 格式內容，不要使用任何多餘包裝。
"""


def build_statement_prompt(concept_yaml: str, ref_statement: str = "") -> str:
  ref_text = ""
  if ref_statement:
    ref_text = f"\n【參考題面風格與排版範例】：\n```markdown\n{ref_statement}\n```\n"

  return f"""【任務二：生成 statement.md】
根據以下的 `concept.yaml` 核心規格，撰寫一份符合 DOMjudge 規範的繁體中文題面 Markdown。

【題目核心概念】：
```yaml
{concept_yaml}
```
{ref_text}
【嚴格格式要求】：
1. 頂端必須包含 YAML Frontmatter (id, title, timelimit, memory, samples, validator_flags)。
2. 第 1 行為 `# <ID> - <完整題目名稱>`。
3. 必須且僅能包含以下順序章節：
   - `### 題目敘述` (情境背景、條列需求，重點可用引用塊 `> `)
   - `### 輸入說明` (行數、變數定義、LaTeX 範圍如 `$N\\ (1 \\le N \\le 10^5)$`)
   - `### 輸出說明` (輸出格式、小數點說明)
   - `### 範例輸入 #1` (反引號 code block)
   - `### 範例輸出 #1` (反引號 code block)
   - `### 範例說明 #1` (條列計算過程)
   - `### 範例輸入 #2`
   - `### 範例輸出 #2`
   - `### 範例說明 #2`
   - `### 測試資訊` (記憶體限制：XXMB, 時間限制：XXs)
4. 數學符號一律使用單一錢字號 `$expression$`。

請直接輸出標準 Markdown，確保範例輸入輸出計算精確！
"""


def build_solver_prompt(
    concept_yaml: str, statement_md: str, ref_solver: str = ""
) -> str:
  ref_text = ""
  if ref_solver:
    ref_text = f"\n【參考解答與產生器腳本結構】：\n```python\n{ref_solver}\n```\n"

  return f"""【任務三：生成 solver.py】
根據以下題目的 `concept.yaml` 與 `statement.md`，撰寫正解與確定性隨機測資產生器 Python 程式碼。

【概念規格】：
```yaml
{concept_yaml}
```

【題面敘述】：
```markdown
{statement_md}
```
{ref_text}
【嚴格代碼規範】：
1. 必須定義 `def solver():` 函式：
   - 使用標準 `input()` 讀取測資。
   - 計算正解後使用 `print()` 輸出至 stdout。
2. 必須定義 `def generate_inputs(seed=42) -> list[str]:` 函式：
   - 接收 `seed` 參數，使用 `rng = random.Random(seed)` 初始化。
   - 根據題面範圍產生 8 筆隨機且具挑戰性的測資字串（不包含題面公開範例）。
   - 每筆測資字串結尾必須換行 `\\n`。
   - 回傳 `list[str]`。
3. 檔案底部必須包含：
   ```python
   if __name__ == "__main__":
       solver()
   ```

請直接輸出 Python 代碼，保證語法正確無誤、無死迴圈。
"""
