from pathlib import Path
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


def test_phase2_cli():
  print("\n==========================================")
  print("開始執行 Phase 2 CLI 與批次處理驗證測試...")
  print("==========================================")

  # 1. 測試 list 指令
  res = run_cli("list")
  assert res.returncode == 0, f"list 失敗: {res.stderr}"
  assert "DBM" in res.stdout and "DAL" in res.stdout, "list 輸出未包含題目"
  print(" [list] 指令測試通過！")

  # 2. 測試 preview 指令
  res = run_cli("preview", "DAL")
  assert res.returncode == 0, f"preview 失敗: {res.stderr}"
  assert (BASE_DIR / "problems" / "DAL" / "problem.pdf").exists()
  print(" [preview] 指令測試通過！")

  # 3. 測試 check 指令
  res = run_cli("check", "DBM")
  assert res.returncode == 0, f"check 失敗: {res.stderr}"
  assert "[OK] 檢驗全部通過！" in res.stdout
  print(" [check <ID>] 指令測試通過！")

  res = run_cli("check", "--all")
  assert res.returncode == 0, f"check --all 失敗: {res.stderr}"
  assert "DBM" in res.stdout and "DAL" in res.stdout
  print(" [check --all] 批次檢驗測試通過！")

  # 4. 測試 build 單題與批次
  res = run_cli("build", "DBM")
  assert res.returncode == 0, f"build DBM 失敗: {res.stderr}"
  assert (BASE_DIR / "dist" / "DBM.zip").exists()
  print(" [build <ID>] 單題建置測試通過！")

  res = run_cli("build", "--all")
  assert res.returncode == 0, f"build --all 失敗: {res.stderr}"
  assert "[DONE] 批次建置總結" in res.stdout
  assert (BASE_DIR / "dist" / "DAL.zip").exists()
  assert (BASE_DIR / "dist" / "DBM.zip").exists()
  print(" [build --all] 批次建置測試通過！")

  # 5. 測試錯誤題目代號防呆
  res = run_cli("build", "NONEXISTENT_XYZ")
  assert res.returncode != 0, "不存在的題目應返回非零錯誤碼"
  print(" 錯誤參數與不存在題目防呆測試通過！")

  print("\n Phase 2 所有驗收條件全數通過！")


if __name__ == "__main__":
  test_phase2_cli()
