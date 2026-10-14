import os
import sys
from pathlib import Path
import tempfile
from zipfile import ZipFile

# 將專案根目錄加入模組搜尋路徑
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.builder import build_problem
from core.testcase_runner import run_solver_process
import yaml


def test_phase1_mvp():
  base_dir = Path(__file__).resolve().parent.parent
  problem_dir = base_dir / "problems" / "DBM"
  dist_dir = base_dir / "dist"

  print("\n==========================================")
  print("開始執行 Phase 1 MVP 端到端驗證測試...")
  print("==========================================")

  # 1. 執行標準建置管線
  result = build_problem(
      problem_dir=problem_dir,
      dist_dir=dist_dir,
      template_path=base_dir / "templates" / "html_template.html",
  )

  print(f" 建置成功：{result['id']} - {result['title']}")
  print(f" 題本 PDF：{result['pdf_path']}")
  print(
      f" 測資數量：共 {result['testcases_count']} 筆 (公開 {result['samples_count']}"
      f" 筆 / 隱藏 {result['secret_count']} 筆)"
  )
  print(f" 發布 ZIP：{result['zip_path']}")

  # 2. 驗證產物存在與尺寸
  assert result["pdf_path"].exists(), "PDF 檔案未產出"
  assert result["pdf_path"].stat().st_size > 1000, "PDF 檔案大小異常"

  tc_dir = problem_dir / "testcases"
  assert tc_dir.exists(), "testcases 目錄未產出"
  in_files = list(tc_dir.glob("*.in"))
  ans_files = list(tc_dir.glob("*.ans"))
  assert len(in_files) == 10, f"預期 10 筆 .in，實際為 {len(in_files)}"
  assert len(ans_files) == 10, f"預期 10 筆 .ans，實際為 {len(ans_files)}"

  zip_path = result["zip_path"]
  assert zip_path.exists(), "ZIP 發布包未產出"
  assert zip_path.stat().st_size > 1000, "ZIP 檔案大小異常"

  # 3. 檢驗 ZIP 內部結構與 DOMjudge 7.3.3 標準相容性
  with ZipFile(zip_path, "r") as zf:
    namelist = zf.namelist()
    assert "problem.pdf" in namelist, "ZIP 缺少 problem.pdf"
    assert "domjudge-problem.ini" in namelist, "ZIP 缺少 domjudge-problem.ini"
    assert "problem.yaml" in namelist, "ZIP 缺少 problem.yaml"

    # 驗證 sample/secret 分流
    assert "data/sample/01.in" in namelist, "ZIP sample 缺少 01.in"
    assert "data/sample/01.ans" in namelist, "ZIP sample 缺少 01.ans"
    assert "data/sample/02.in" in namelist, "ZIP sample 缺少 02.in"
    assert "data/sample/02.ans" in namelist, "ZIP sample 缺少 02.ans"
    assert "data/secret/03.in" in namelist, "ZIP secret 缺少 03.in"
    assert "data/secret/10.ans" in namelist, "ZIP secret 缺少 10.ans"

    # 驗證 ini 內容
    ini_text = zf.read("domjudge-problem.ini").decode("utf-8")
    assert "timelimit='1'" in ini_text, f"ini 內容不符: {ini_text}"

    # 驗證 yaml 內容
    yaml_text = zf.read("problem.yaml").decode("utf-8")
    yaml_obj = yaml.safe_load(yaml_text)
    assert "DBM" in yaml_obj["name"]
    assert yaml_obj["limits"]["memory"] == 64
    assert "float_tolerance 1E-3" in yaml_obj.get("validator_flags", "")

  print(" 產物結構與 DOMjudge 7.3.3 標準檢查通過！")

  # 4. 驗證超時防護機制 (Timeout Protection)
  with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
    f.write("import time\nwhile True:\n    time.sleep(0.1)\n")
    infinite_loop_py = f.name

  try:
    timeout_triggered = False
    try:
      run_solver_process(infinite_loop_py, "test", timeout=1.0)
    except TimeoutError:
      timeout_triggered = True
    assert (
        timeout_triggered
    ), "超時保護未生效！死迴圈程式未在指定秒數內被強制終止。"
    print(" 死迴圈超時終止 (Timeout Protection) 測試通過！")
  finally:
    if os.path.exists(infinite_loop_py):
      os.remove(infinite_loop_py)

  # 5. 驗證交叉檢驗防呆機制 (Sanity Check)
  from core.testcase_runner import generate_and_verify_testcases
  mismatched_sample = [{
      "id": 1,
      "input_clean": "4\n2\n6\n20\n15\n18\n",
      "output_clean": "999.0\n0.0\n0.0\n0.0\n" # 故意寫錯的期望輸出
  }]
  sanity_failed = False
  try:
    generate_and_verify_testcases(problem_dir, mismatched_sample)
  except ValueError as e:
    if "Sanity Check 失敗" in str(e):
      sanity_failed = True
  assert sanity_failed, "Sanity Check 防呆未生效！題面與解答輸出不一致時未報錯。"
  print(" 自動交叉檢驗 (Sanity Check 防呆) 測試通過！")

  print("\n Phase 1 所有驗收條件全數通過！")


if __name__ == "__main__":
  test_phase1_mvp()
