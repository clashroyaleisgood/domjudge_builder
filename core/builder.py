from pathlib import Path
from core.markdown_engine import (
    parse_and_validate_markdown,
    render_html_from_markdown,
)
from core.packager import build_domjudge_zip
from core.pdf_engine import compile_html_to_pdf
from core.spec import ProblemSpec, load_spec
from core.testcase_runner import generate_and_verify_testcases


def build_problem(
    problem_dir: Path | str,
    dist_dir: Path | str = "dist",
    template_path: Path | str = "templates/html_template.html",
    timeout: float = 5.0,
    seed: int = 42,
) -> dict:
  """執行單題完整建置管線：

  1. 解析 concept.yaml / statement.md 取得題目規格
  2. 驗證題面格式並提取範例測資
  3. 渲染題面為 A4 PDF (Edge Headless)
  4. 生成測資並執行 Sanity Check (subprocess 隔離與超時終止)
  5. 封裝 DOMjudge 7.3.3 標準 ZIP
  """
  problem_dir = Path(problem_dir).resolve()
  template_path = Path(template_path).resolve()
  dist_dir = Path(dist_dir).resolve()

  statement_file = problem_dir / "statement.md"
  if not statement_file.exists():
    raise FileNotFoundError(f"在 {problem_dir} 中找不到 statement.md")

  # 1. 載入題目規格
  spec: ProblemSpec = load_spec(problem_dir)

  # 2. 解析題面並提取範例
  with open(statement_file, "r", encoding="utf-8") as f:
    statement_raw = f.read()
  parsed_md = parse_and_validate_markdown(statement_raw)

  # 3. 渲染 HTML 並編譯 PDF
  html_content = render_html_from_markdown(parsed_md, spec, template_path)
  pdf_path = problem_dir / "problem.pdf"
  compile_html_to_pdf(html_content, pdf_path)

  # 4. 產生測試資料與自動交叉驗證 (Sanity Check)
  tc_pairs = generate_and_verify_testcases(
      problem_dir, parsed_md["samples"], seed=seed, timeout=timeout
  )

  # 5. 打包 DOMjudge 壓縮包
  zip_path = build_domjudge_zip(
      problem_dir, spec, dist_dir=dist_dir, pdf_path=pdf_path
  )

  return {
      "id": spec.id,
      "title": spec.title,
      "pdf_path": pdf_path,
      "testcases_count": len(tc_pairs),
      "samples_count": spec.samples,
      "secret_count": len(tc_pairs) - spec.samples,
      "zip_path": zip_path,
  }
