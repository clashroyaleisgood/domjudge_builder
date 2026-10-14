import os
from pathlib import Path
import re
from jinja2 import Template
import markdown
from core.spec import ProblemSpec


def strip_frontmatter(content: str) -> str:
  """移除 Markdown 頂端的 YAML Frontmatter (若存在)"""
  return re.sub(r"^---\s*\n.*?\n---\s*", "", content, flags=re.DOTALL).strip()


def extract_code_block_content(text: str) -> str:
  """提取 Code Block 內部的純文字 (去除 ``` 包覆) 並確保結尾換行"""
  text = text.strip()
  m = re.match(r"^```[a-zA-Z0-9_-]*\s*\n([\s\S]*?)\n```$", text)
  if m:
    return m.group(1).strip() + "\n"
  # 若未被反引號包覆則直接去頭尾空白並換行
  return text.strip() + "\n"


def parse_and_validate_markdown(content: str) -> dict:
  """解析 Markdown 題目文件，驗證四大必要章節與連續範例，並提取結構化資料。"""
  clean_content = strip_frontmatter(content)

  # 1. 檢查大標題
  title_match = re.search(r"^# (.+)", clean_content, re.MULTILINE)
  if not title_match:
    raise ValueError("Markdown 格式錯誤：缺少頂層大標題 (# 題目名稱)")
  title = title_match.group(1).strip()

  # 2. 切割章節
  section_pattern = r"### (.+?)\n(.*?)(?=\n### |\Z)"
  raw_sections = re.findall(section_pattern, clean_content, re.DOTALL)
  if not raw_sections:
    raise ValueError("Markdown 格式錯誤：找不到任何 '### 章節' 標題")

  data = {}
  samples_map = {}

  for name, body in raw_sections:
    name = name.strip()
    body = body.strip()

    sample_match = re.match(r"範例(輸入|輸出|說明)(?: #(\d+))?", name)
    if sample_match:
      kind = sample_match.group(1)
      idx_str = sample_match.group(2)

      if not idx_str:
        continue
      idx = int(idx_str)

      if idx not in samples_map:
        samples_map[idx] = {"input": "", "output": "", "explanation": ""}

      if kind == "輸入":
        samples_map[idx]["input"] = body
      elif kind == "輸出":
        samples_map[idx]["output"] = body
      elif kind == "說明":
        samples_map[idx]["explanation"] = body
    else:
      data[name] = body

  # 3. 驗證必要章節
  required = ["題目敘述", "輸入說明", "輸出說明", "測試資訊"]
  for req in required:
    if req not in data:
      raise ValueError(f"Markdown 格式錯誤：缺少必要章節 '### {req}'")

  # 4. 驗證範例編號完整性與連續性
  sample_indices = sorted(samples_map.keys())
  if not sample_indices:
    raise ValueError("Markdown 格式錯誤：缺少範例輸入與輸出 (範例 #1)")

  expected_indices = list(range(1, len(sample_indices) + 1))
  if sample_indices != expected_indices:
    raise ValueError(
        f"Markdown 格式錯誤：範例編號必須連續且從 1 開始，當前為: {sample_indices}"
    )

  samples = []
  for idx in sample_indices:
    item = samples_map[idx]
    if not item["input"] or not item["output"]:
      raise ValueError(f"Markdown 格式錯誤：範例 #{idx} 缺少輸入或輸出內容")

    samples.append({
        "id": idx,
        "input_raw": item["input"],
        "output_raw": item["output"],
        "input_clean": extract_code_block_content(item["input"]),
        "output_clean": extract_code_block_content(item["output"]),
        "explanation": item["explanation"],
    })

  return {
      "title": title,
      "sections": data,
      "samples": samples,
      "clean_content": clean_content,
  }


def render_html_from_markdown(
    parsed_data: dict,
    spec: ProblemSpec,
    template_path: Path | str,
) -> str:
  """將解析後的題目資料填入印刷 HTML 模板，渲染為適合列印之 HTML。"""

  def md_to_html(text: str, process_math: bool = False) -> str:
    rendered = markdown.markdown(text, extensions=["fenced_code"])
    if process_math:
      # 將 $...$ 轉換為 MathJax 相容之 \(...\)
      rendered = re.sub(r"\$(.*?)\$", r"\\(\1\\)", rendered)
    return rendered

  template_path = Path(template_path)
  with open(template_path, "r", encoding="utf-8") as f:
    template = Template(f.read())

  sections = parsed_data["sections"]
  samples = parsed_data["samples"]

  # 顯示標題：優先取 spec.title，或使用 Markdown 大標題
  display_title = (
      f"{spec.id} - {spec.title}"
      if not parsed_data["title"].startswith(spec.id)
      else parsed_data["title"]
  )

  html = template.render(
      title=display_title,
      statement=md_to_html(sections.get("題目敘述", ""), process_math=True),
      input_desc=md_to_html(sections.get("輸入說明", ""), process_math=True),
      output_desc=md_to_html(sections.get("輸出說明", ""), process_math=True),
      hint=md_to_html(sections.get("提示", ""), process_math=True)
      if "提示" in sections
      else "",
      limits=md_to_html(sections.get("測試資訊", ""), process_math=True),
      samples=[
          {
              "id": s["id"],
              "input": md_to_html(s["input_raw"]),
              "output": md_to_html(s["output_raw"]),
              "explanation": md_to_html(
                  s["explanation"], process_math=True
              ),
          }
          for s in samples
      ],
  )
  return html
