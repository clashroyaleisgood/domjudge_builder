import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
CLI = str(BASE_DIR / "domjudge_cli.py")


def run_cli(*args):
  cmd = [PYTHON, CLI] + list(args)
  return subprocess.run(
      cmd,
      capture_output=True,
      text=True,
      encoding="utf-8",
      errors="replace",
      cwd=str(BASE_DIR),
  )


def test_phase3_ai():
  print("\n==========================================")
  print("開始執行 Phase 3 AI 協同生成模組驗證測試...")
  print("==========================================")

  test_pid = "DCA"
  test_prob_dir = BASE_DIR / "problems" / test_pid

  # 清理可能存在的舊測試資料夾
  if test_prob_dir.exists():
    shutil.rmtree(test_prob_dir)

  # 1. 測試 CLI generate --all (透過 Mock 客戶端)
  res = run_cli(
      "generate",
      test_pid,
      "--all",
      "--prompt",
      "小明買了披薩想要跟朋友們平分",
      "--api-key",
      "mock",
  )
  assert res.returncode == 0, f"generate 失敗: {res.stderr}"
  assert "[OK] AI 生成流程完畢！" in res.stdout
  print(" [generate --all] 呼叫成功！")

  # 2. 驗證生成檔案存在且內容合規
  concept_file = test_prob_dir / "concept.yaml"
  statement_file = test_prob_dir / "statement.md"
  solver_file = test_prob_dir / "solver.py"

  assert concept_file.exists(), "concept.yaml 未生成"
  assert statement_file.exists(), "statement.md 未生成"
  assert solver_file.exists(), "solver.py 未生成"

  concept_text = concept_file.read_text(encoding="utf-8")
  assert "DCA" in concept_text
  assert "timelimit: 1.0" in concept_text

  statement_text = statement_file.read_text(encoding="utf-8")
  assert "### 題目敘述" in statement_text
  assert "### 範例輸入 #1" in statement_text

  solver_text = solver_file.read_text(encoding="utf-8")
  assert "def solver():" in solver_text
  assert "def generate_inputs(" in solver_text

  print(" AI 生成檔案規格檢核通過！")

  # 3. 驗證 AI 生成的題目能無縫接入 Core 編譯管線 (check & build)
  res_check = run_cli("check", test_pid)
  assert res_check.returncode == 0, f"check DCA 失敗: {res_check.stderr}"
  assert "[OK] 檢驗全部通過！" in res_check.stdout
  print(" AI 生成題目 Sanity Check 交叉檢驗通過！")

  res_build = run_cli("build", test_pid)
  assert res_build.returncode == 0, f"build DCA 失敗: {res_build.stderr}"
  assert (BASE_DIR / "dist" / f"{test_pid}.zip").exists()
  assert (test_prob_dir / "problem.pdf").exists()
  print(" AI 生成題目正式編譯與打包通過！")

  # 4. 清理測試題目
  if test_prob_dir.exists():
    shutil.rmtree(test_prob_dir)
  dist_zip = BASE_DIR / "dist" / f"{test_pid}.zip"
  if dist_zip.exists():
    dist_zip.unlink()

  print("\n Phase 3 所有驗收條件全數通過！")


if __name__ == "__main__":
  test_phase3_ai()
