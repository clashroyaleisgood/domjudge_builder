import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys


def run_solver_process(
    solver_path: Path | str, test_input: str, timeout: float = 5.0
) -> str:
  """以獨立 subprocess 行程執行 solver.py，原生提供環境隔離與超時保護。"""
  solver_path = Path(solver_path).resolve()
  if not solver_path.exists():
    raise FileNotFoundError(f"找不到解答腳本：{solver_path}")

  cmd = [sys.executable, str(solver_path)]

  try:
    res = subprocess.run(
        cmd,
        input=test_input,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(solver_path.parent),
    )
  except subprocess.TimeoutExpired as e:
    raise TimeoutError(
        f"Solver 執行逾時 (超過 {timeout} 秒)！請檢查是否存在死迴圈。"
    ) from e

  if res.returncode != 0:
    raise RuntimeError(
        f"Solver 執行崩潰 (return code {res.returncode}):\n{res.stderr}"
    )

  return res.stdout


def load_generator_function(solver_path: Path | str):
  """動態匯入 solver.py 模組以取得 generate_inputs 函式。"""
  solver_path = Path(solver_path).resolve()
  spec = importlib.util.spec_from_file_location("solver_module", solver_path)
  if not spec or not spec.loader:
    return None

  module = importlib.util.module_from_spec(spec)
  try:
    spec.loader.exec_module(module)
    return getattr(module, "generate_inputs", None)
  except Exception as e:
    raise RuntimeError(f"載入 {solver_path.name} 模組失敗：{e}") from e


def _normalize_output(text: str) -> list[str]:
  """標準化輸出字串（去除頭尾空白並按行比對）"""
  return [line.strip() for line in text.strip().splitlines() if line.strip()]


def generate_and_verify_testcases(
    problem_dir: Path | str,
    sample_cases: list[dict],
    seed: int = 42,
    timeout: float = 5.0,
) -> list[tuple[Path, Path]]:
  """產生所有測試資料，執行自動交叉比對 (Sanity Check)，並寫入 testcases/ 目錄。"""
  problem_dir = Path(problem_dir).resolve()
  solver_path = problem_dir / "solver.py"
  testcases_dir = problem_dir / "testcases"

  if not solver_path.exists():
    raise FileNotFoundError(f"在 {problem_dir} 中找不到 solver.py")

  # 1. 取得隨機測資清單
  gen_func = load_generator_function(solver_path)
  random_inputs = []
  if callable(gen_func):
    random_inputs = gen_func(seed=seed)
    if not isinstance(random_inputs, list):
      raise TypeError(
          f"generate_inputs() 回傳值必須是 list[str]，實際為 {type(random_inputs)}"
      )

  # 2. 合併測資清單：範例測資優先，其後接隨機測資
  sample_inputs = [s["input_clean"] for s in sample_cases]
  all_inputs = sample_inputs + random_inputs

  if not all_inputs:
    raise ValueError("未產出任何測試資料（題面無範例且未提供隨機測資產生器）")

  # 3. 交叉比對 (Sanity Check)：檢驗題面上的範例輸出是否與正解一致
  for s in sample_cases:
    actual_out = run_solver_process(
        solver_path, s["input_clean"], timeout=timeout
    )
    norm_actual = _normalize_output(actual_out)
    norm_expected = _normalize_output(s["output_clean"])

    if norm_actual != norm_expected:
      raise ValueError(
          f"【Sanity Check 失敗】題面範例 #{s['id']} 的輸出與 solver 產出不一致！\n"
          f"--- 題面宣告期望 ---\n{s['output_clean']}\n"
          f"--- 正解實際產出 ---\n{actual_out}"
      )

  # 4. 清理並重建 testcases/ 目錄
  if testcases_dir.exists():
    for f in testcases_dir.glob("*"):
      if f.is_file() and (f.suffix in [".in", ".ans"]):
        f.unlink()
  else:
    testcases_dir.mkdir(parents=True, exist_ok=True)

  # 5. 逐一執行測資並寫入硬碟
  testcase_pairs = []
  for idx, test_in in enumerate(all_inputs, start=1):
    test_out = run_solver_process(solver_path, test_in, timeout=timeout)

    in_file = testcases_dir / f"{idx:02d}.in"
    ans_file = testcases_dir / f"{idx:02d}.ans"

    with open(in_file, "w", encoding="utf-8") as f:
      f.write(test_in)

    with open(ans_file, "w", encoding="utf-8") as f:
      f.write(test_out)

    testcase_pairs.append((in_file, ans_file))

  return testcase_pairs
