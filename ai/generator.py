from pathlib import Path
import re
from ai.client import LLMClient
from ai.prompts import (
    SYSTEM_PROMPT,
    build_concept_prompt,
    build_solver_prompt,
    build_statement_prompt,
)


def _strip_markdown_code_wrap(text: str, lang: str = "") -> str:
  """移除 LLM 回應外層的反引號代碼方塊包裝 (例如 ```yaml ... ```)"""
  text = text.strip()
  pattern = rf"^```{lang}\s*\n([\s\S]*?)\n```$"
  m = re.match(pattern, text, re.IGNORECASE)
  if m:
    return m.group(1).strip()
  # 通用反引號包裝去除
  m_generic = re.match(r"^```[a-zA-Z0-9_-]*\s*\n([\s\S]*?)\n```$", text)
  if m_generic:
    return m_generic.group(1).strip()
  return text


def generate_concept_file(
    problem_id: str,
    prompt: str,
    ref_ids: list[str] = None,
    client: LLMClient = None,
    problems_dir: Path | str = "problems",
) -> Path:
  """調用 LLM 將出題構想收斂為標準 concept.yaml"""
  client = client or LLMClient()
  problems_base = Path(problems_dir).resolve()
  problem_dir = problems_base / problem_id
  problem_dir.mkdir(parents=True, exist_ok=True)

  # 讀取參考題目的 concept 規格
  ref_concepts = []
  if ref_ids:
    for ref in ref_ids:
      c_path = problems_base / ref / "concept.yaml"
      if c_path.exists():
        ref_concepts.append(c_path.read_text(encoding="utf-8"))

  prompt_text = build_concept_prompt(
      problem_id, prompt, ref_concepts=ref_concepts
  )
  raw_yaml = client.generate(prompt_text, system_prompt=SYSTEM_PROMPT)
  clean_yaml = _strip_markdown_code_wrap(raw_yaml, lang="yaml")

  concept_file = problem_dir / "concept.yaml"
  with open(concept_file, "w", encoding="utf-8") as f:
    f.write(clean_yaml + "\n")

  return concept_file


def generate_statement_file(
    problem_id: str,
    client: LLMClient = None,
    problems_dir: Path | str = "problems",
    ref_id: str = "DBM",
) -> Path:
  """根據 concept.yaml 推導生成標準格式的 statement.md"""
  client = client or LLMClient()
  problems_base = Path(problems_dir).resolve()
  problem_dir = problems_base / problem_id

  concept_file = problem_dir / "concept.yaml"
  if not concept_file.exists():
    raise FileNotFoundError(
        f"在 {problem_dir} 中找不到 concept.yaml，請先生成核心概念規格。"
    )

  concept_content = concept_file.read_text(encoding="utf-8")

  ref_statement = ""
  if ref_id:
    r_path = problems_base / ref_id / "statement.md"
    if r_path.exists():
      ref_statement = r_path.read_text(encoding="utf-8")

  prompt_text = build_statement_prompt(
      concept_content, ref_statement=ref_statement
  )
  raw_md = client.generate(prompt_text, system_prompt=SYSTEM_PROMPT)
  clean_md = _strip_markdown_code_wrap(raw_md, lang="markdown")

  statement_file = problem_dir / "statement.md"
  with open(statement_file, "w", encoding="utf-8") as f:
    f.write(clean_md + "\n")

  return statement_file


def generate_solver_file(
    problem_id: str,
    client: LLMClient = None,
    problems_dir: Path | str = "problems",
    ref_id: str = "DBM",
) -> Path:
  """根據 concept.yaml 與 statement.md 推導生成正解與隨機測資腳本 solver.py"""
  client = client or LLMClient()
  problems_base = Path(problems_dir).resolve()
  problem_dir = problems_base / problem_id

  concept_file = problem_dir / "concept.yaml"
  statement_file = problem_dir / "statement.md"

  if not concept_file.exists() or not statement_file.exists():
    raise FileNotFoundError(
        f"生成 solver.py 需要同時具備 concept.yaml 與 statement.md"
    )

  concept_content = concept_file.read_text(encoding="utf-8")
  statement_content = statement_file.read_text(encoding="utf-8")

  ref_solver = ""
  if ref_id:
    r_path = problems_base / ref_id / "solver.py"
    if r_path.exists():
      ref_solver = r_path.read_text(encoding="utf-8")

  prompt_text = build_solver_prompt(
      concept_content, statement_content, ref_solver=ref_solver
  )
  raw_py = client.generate(prompt_text, system_prompt=SYSTEM_PROMPT)
  clean_py = _strip_markdown_code_wrap(raw_py, lang="python")

  solver_file = problem_dir / "solver.py"
  with open(solver_file, "w", encoding="utf-8") as f:
    f.write(clean_py + "\n")

  return solver_file
