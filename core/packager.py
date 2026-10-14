import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from core.spec import ProblemSpec
import yaml


def build_domjudge_zip(
    problem_dir: Path | str,
    spec: ProblemSpec,
    dist_dir: Path | str = "dist",
    pdf_path: Path | str | None = None,
) -> Path:
  """將題目編譯產物打包為符合 DOMjudge 7.3.3 標準的 ZIP 題目包。"""
  problem_dir = Path(problem_dir).resolve()
  dist_dir = Path(dist_dir).resolve()
  dist_dir.mkdir(parents=True, exist_ok=True)

  zip_path = dist_dir / f"{spec.id}.zip"

  # 1. 尋找 problem.pdf
  pdf_file = Path(pdf_path) if pdf_path else (problem_dir / "problem.pdf")
  if not pdf_file.exists():
    raise FileNotFoundError(f"找不到題本 PDF 檔案：{pdf_file}")

  # 2. 尋找 testcases
  testcases_dir = problem_dir / "testcases"
  if not testcases_dir.exists():
    raise FileNotFoundError(f"找不到測試資料目錄：{testcases_dir}")

  # 3. 動態組裝 domjudge-problem.ini
  timelimit_str = (
      str(int(spec.timelimit))
      if spec.timelimit.is_integer()
      else str(spec.timelimit)
  )
  ini_content = f"timelimit='{timelimit_str}'\n"

  # 4. 動態組裝 problem.yaml
  yaml_data = {
      "name": (
          f"{spec.id} - {spec.title}"
          if not spec.title.startswith(spec.id)
          else spec.title
      ),
      "limits": {"memory": spec.memory},
  }
  if spec.validator_flags:
    yaml_data["validator_flags"] = spec.validator_flags
  yaml_content = yaml.dump(
      yaml_data, allow_unicode=True, default_flow_style=False
  )

  # 5. 打包 ZIP (自動安全覆寫)
  with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
    # 寫入設定檔與 PDF
    zf.writestr("domjudge-problem.ini", ini_content)
    zf.writestr("problem.yaml", yaml_content)
    zf.write(pdf_file, "problem.pdf")

    # 寫入測資 (sample/secret 分流)
    tc_files = sorted(testcases_dir.glob("*"))
    sample_count = 0
    secret_count = 0

    for tc_file in tc_files:
      if not tc_file.is_file() or tc_file.suffix not in [".in", ".ans"]:
        continue

      base = tc_file.stem
      is_sample = False
      if spec.samples > 0 and base.isdigit() and int(base) <= spec.samples:
        is_sample = True

      target_subfolder = "sample" if is_sample else "secret"
      arcname = f"data/{target_subfolder}/{tc_file.name}"
      zf.write(tc_file, arcname)

      if tc_file.suffix == ".in":
        if is_sample:
          sample_count += 1
        else:
          secret_count += 1

  return zip_path
