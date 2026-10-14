import re
from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class ProblemSpec:
  id: str
  title: str
  timelimit: float = 1.0
  memory: int = 64
  samples: int = 0
  validator_flags: str = ""

  def to_dict(self) -> dict:
    return {
        "id": self.id,
        "title": self.title,
        "timelimit": self.timelimit,
        "memory": self.memory,
        "samples": self.samples,
        "validator_flags": self.validator_flags,
    }


def _extract_title_from_md(md_content: str) -> str:
  """從 Markdown 大標題中提取題目名稱 (例如 '# DBM - 製作餅乾...' -> '製作餅乾...')"""
  for line in md_content.splitlines():
    line = line.strip()
    if line.startswith("# "):
      raw_title = line[2:].strip()
      if " - " in raw_title:
        return raw_title.split(" - ", 1)[1].strip()
      return raw_title
  return ""


def load_spec(problem_dir: Path | str) -> ProblemSpec:
  """優先讀取 concept.yaml；若無則自動 fallback 解析 statement.md 的 YAML Frontmatter。"""
  problem_dir = Path(problem_dir)
  concept_path = problem_dir / "concept.yaml"
  statement_path = problem_dir / "statement.md"

  data = {}
  title = ""
  prob_id = problem_dir.name

  if concept_path.exists():
    with open(concept_path, "r", encoding="utf-8") as f:
      data = yaml.safe_load(f) or {}

  elif statement_path.exists():
    with open(statement_path, "r", encoding="utf-8") as f:
      content = f.read()
    match = re.match(r"^---\s*\n(.*?)\n---\s*", content, re.DOTALL)
    if match:
      data = yaml.safe_load(match.group(1)) or {}
    title = _extract_title_from_md(content)
  else:
    raise FileNotFoundError(
        f"在 {problem_dir} 中找不到 concept.yaml 或 statement.md"
    )

  # 欄位解析與寬容處理
  prob_id = str(data.get("id") or prob_id)
  title = str(data.get("title") or data.get("name") or title or prob_id)

  # limits 區塊寬容（支援平鋪或巢狀 limits: 結構）
  limits = data.get("limits", {})
  if not isinstance(limits, dict):
    limits = {}

  timelimit = float(data.get("timelimit") or limits.get("timelimit") or 1.0)
  memory = int(data.get("memory") or limits.get("memory") or 64)
  samples = int(data.get("samples") or limits.get("samples") or 0)

  validator_flags = str(
      data.get("validator_flags")
      or limits.get("validator_flags")
      or (
          f"float_tolerance {limits['float_tolerance']}"
          if "float_tolerance" in limits
          else ""
      )
  )

  # 若 title 仍為空，嘗試由 statement.md 補足
  if (not title or title == prob_id) and statement_path.exists():
    with open(statement_path, "r", encoding="utf-8") as f:
      t = _extract_title_from_md(f.read())
      if t:
        title = t

  return ProblemSpec(
      id=prob_id,
      title=title,
      timelimit=timelimit,
      memory=memory,
      samples=samples,
      validator_flags=validator_flags,
  )
