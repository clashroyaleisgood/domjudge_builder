import argparse
import os
from pathlib import Path
import sys
import time

# 確保專案根目錄在 sys.path 中
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
  sys.path.insert(0, str(BASE_DIR))

# Windows 命令列編碼防護 (防止 cp950 遇到特殊字元崩潰)
if sys.platform == "win32":
  if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
  if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from core.builder import (
    build_problem,
    check_problem,
    discover_problems,
    preview_problem,
)
from core.spec import load_spec


def find_problem_dir(problem_id: str, problems_base: Path) -> Path:
  """根據題目代號尋找對應的題目資料夾"""
  # 優先精確比對
  exact_path = problems_base / problem_id
  if exact_path.is_dir():
    return exact_path

  # 忽略大小寫比對
  for p in problems_base.iterdir():
    if p.is_dir() and p.name.lower() == problem_id.lower():
      return p

  raise FileNotFoundError(
      f"在 {problems_base} 中找不到題目代號為 '{problem_id}' 的資料夾"
  )


def cmd_build(args):
  problems_base = BASE_DIR / "problems"
  dist_dir = BASE_DIR / args.dist

  if args.all:
    target_dirs = discover_problems(problems_base)
    if not target_dirs:
      print(f" 在 {problems_base} 中未發現任何合規題目。")
      return 0

    print(
        f"\n[BUILD] 開始批次建置所有題目 (共 {len(target_dirs)} 題，Seed={args.seed})..."
    )
    print("=" * 60)

    success_count = 0
    fail_count = 0
    start_time = time.time()

    for idx, p_dir in enumerate(target_dirs, start=1):
      p_name = p_dir.name
      print(f"[{idx}/{len(target_dirs)}] 建置 {p_name} ...", end=" ", flush=True)
      try:
        res = build_problem(
            problem_dir=p_dir,
            dist_dir=dist_dir,
            seed=args.seed,
            timeout=args.timeout,
        )
        print("[OK]")
        print(f"    - 題名: {res['title']}")
        print(
            f"    - 測資: {res['testcases_count']} 筆 (公開"
            f" {res['samples_count']} / 隱藏 {res['secret_count']})"
        )
        print(f"    - 封包: {res['zip_path'].relative_to(BASE_DIR)}")
        success_count += 1
      except Exception as e:
        print(f"[FAIL]: {e}")
        fail_count += 1

    elapsed = time.time() - start_time
    print("=" * 60)
    print(
        f"[DONE] 批次建置總結：成功 {success_count} 題，失敗 {fail_count} 題"
        f" (耗時 {elapsed:.2f} 秒)"
    )
    return 1 if fail_count > 0 else 0

  else:
    if not args.id:
      print("錯誤：請指定題目代號 (例如 'DBM')，或使用 --all 批次建置。")
      return 1

    try:
      p_dir = find_problem_dir(args.id, problems_base)
      print(f"[BUILD] 開始建置題目 {args.id}...")
      res = build_problem(
          problem_dir=p_dir,
          dist_dir=dist_dir,
          seed=args.seed,
          timeout=args.timeout,
      )
      print(f"\n[OK] 建置成功！")
      print(f"  - 題目代號: {res['id']}")
      print(f"  - 完整題名: {res['title']}")
      print(f"  - 題本 PDF: {res['pdf_path']}")
      print(
          f"  - 測試資料: {res['testcases_count']} 筆 (公開 {res['samples_count']}"
          f" / 隱藏 {res['secret_count']})"
      )
      print(f"  - 發布 ZIP: {res['zip_path']}")
      return 0
    except Exception as e:
      print(f"\n[FAIL] 建置失敗：{e}")
      return 1


def cmd_preview(args):
  problems_base = BASE_DIR / "problems"
  try:
    p_dir = find_problem_dir(args.id, problems_base)
    print(f"[PREVIEW] 正在為 {args.id} 渲染題本 PDF...")
    pdf_path = preview_problem(p_dir)
    print(f"[OK] 題本 PDF 渲染完成：{pdf_path}")
    return 0
  except Exception as e:
    print(f"[FAIL] 預覽渲染失敗：{e}")
    return 1


def cmd_check(args):
  problems_base = BASE_DIR / "problems"
  if args.all:
    target_dirs = discover_problems(problems_base)
    print(f"\n[CHECK] 開始交叉檢驗所有題目 (共 {len(target_dirs)} 題)...")
    fail_count = 0
    for idx, p_dir in enumerate(target_dirs, start=1):
      try:
        res = check_problem(p_dir, seed=args.seed, timeout=args.timeout)
        print(
            f"  [{idx}/{len(target_dirs)}] {res['id']} - {res['title']}: [OK]"
            f" (範例 {res['samples_count']} 筆 / 總測資"
            f" {res['total_cases']} 筆)"
        )
      except Exception as e:
        print(f"  [{idx}/{len(target_dirs)}] {p_dir.name}: [FAIL] 異常: {e}")
        fail_count += 1
    return 1 if fail_count > 0 else 0
  else:
    if not args.id:
      print("錯誤：請指定題目代號或使用 --all")
      return 1
    try:
      p_dir = find_problem_dir(args.id, problems_base)
      print(f"[CHECK] 正在對 {args.id} 執行語法與 Sanity Check 檢驗...")
      res = check_problem(p_dir, seed=args.seed, timeout=args.timeout)
      print(f"[OK] 檢驗全部通過！")
      print(f"  - 題目: {res['id']} - {res['title']}")
      print(f"  - 公開範例數: {res['samples_count']} 筆 (交叉比對吻合)")
      print(f"  - 總測資生成: {res['total_cases']} 筆 (含隨機測資)")
      return 0
    except Exception as e:
      print(f"[FAIL] 檢驗失敗：{e}")
      return 1


def cmd_list(args):
  problems_base = BASE_DIR / "problems"
  target_dirs = discover_problems(problems_base)
  dist_dir = BASE_DIR / "dist"

  print(f"\n[LIST] 題目庫現況 (共 {len(target_dirs)} 題)")
  print("-" * 75)
  print(
      f"{'ID':<8} {'Title':<26} {'Concept':<9} {'MD':<6} {'Solver':<8}"
      f" {'PDF':<6} {'ZIP':<6}"
  )
  print("-" * 75)

  for p_dir in target_dirs:
    try:
      spec = load_spec(p_dir)
      title = spec.title[:24]
      pid = spec.id
    except Exception:
      title = "(解析異常)"
      pid = p_dir.name

    has_concept = "✓" if (p_dir / "concept.yaml").exists() else "-"
    has_md = "✓" if (p_dir / "statement.md").exists() else "-"
    has_solver = "✓" if (p_dir / "solver.py").exists() else "-"
    has_pdf = "✓" if (p_dir / "problem.pdf").exists() else "-"
    has_zip = "✓" if (dist_dir / f"{pid}.zip").exists() else "-"

    print(
        f"{pid:<8} {title:<26} {has_concept:<9} {has_md:<6} {has_solver:<8}"
        f" {has_pdf:<6} {has_zip:<6}"
    )

  print("-" * 75)
  return 0


def cmd_generate(args):
  from ai.client import LLMClient
  from ai.generator import (
      generate_concept_file,
      generate_solver_file,
      generate_statement_file,
  )

  client = LLMClient(
      api_key=args.api_key,
      provider=args.provider,
      model=args.model,
      base_url=args.base_url,
  )
  problem_id = args.id.upper()
  ref_ids = [r.strip() for r in args.ref.split(",") if r.strip()]

  do_concept = (
      args.concept or args.all or (not args.statement and not args.solver)
  )
  do_statement = args.statement or args.all
  do_solver = args.solver or args.all

  print(f"[AI] 開始為 {problem_id} 執行 AI 協同生成...")

  try:
    if do_concept:
      if not args.prompt and not (
          BASE_DIR / "problems" / problem_id / "concept.yaml"
      ).exists():
        print("錯誤：生成 concept 需要提供 --prompt '題目構想描述'")
        return 1
      if args.prompt:
        print(
            f"  [1/3] 正在收斂核心概念規格 (concept.yaml)...",
            end=" ",
            flush=True,
        )
        c_path = generate_concept_file(
            problem_id, args.prompt, ref_ids=ref_ids, client=client
        )
        print(f"[OK] -> {c_path.relative_to(BASE_DIR)}")

    if do_statement:
      print(
          f"  [2/3] 正在推導題目敘述題本 (statement.md)...",
          end=" ",
          flush=True,
      )
      s_path = generate_statement_file(problem_id, client=client)
      print(f"[OK] -> {s_path.relative_to(BASE_DIR)}")

    if do_solver:
      print(
          f"  [3/3] 正在生成解答與測資腳本 (solver.py)...",
          end=" ",
          flush=True,
      )
      p_path = generate_solver_file(problem_id, client=client)
      print(f"[OK] -> {p_path.relative_to(BASE_DIR)}")

    print(
        f"\n[OK] AI 生成流程完畢！可使用 'python domjudge_cli.py check {problem_id}'"
        " 進行驗證。"
    )
    return 0
  except Exception as e:
    print(f"\n[FAIL] 生成失敗：{e}")
    return 1


def main():
  parser = argparse.ArgumentParser(
      description="DOMjudge Builder - 現代化題目建置、編譯與打包工具",
      formatter_class=argparse.RawDescriptionHelpFormatter,
  )
  subparsers = parser.add_subparsers(dest="command", help="子指令清單")

  # 1. build 指令
  p_build = subparsers.add_parser(
      "build", help="建置題目 (編譯 PDF、產生測資、打包 ZIP)"
  )
  p_build.add_argument("id", nargs="?", default="", help="題目代號 (例如 DBM)")
  p_build.add_argument("--all", action="store_true", help="批次建置所有題目")
  p_build.add_argument(
      "--seed", type=int, default=42, help="隨機測資 Seed (預設 42)"
  )
  p_build.add_argument(
      "--timeout", type=float, default=5.0, help="Solver 逾時上限秒數 (預設 5.0)"
  )
  p_build.add_argument(
      "--dist", default="dist", help="輸出封包目錄 (預設 dist/)"
  )

  # 2. preview 指令
  p_prev = subparsers.add_parser("preview", help="僅編譯與預覽題本 PDF")
  p_prev.add_argument("id", help="題目代號 (例如 DBM)")

  # 3. check 指令
  p_check = subparsers.add_parser(
      "check", help="僅執行格式驗證與 Sanity Check 交叉檢驗"
  )
  p_check.add_argument("id", nargs="?", default="", help="題目代號 (例如 DBM)")
  p_check.add_argument("--all", action="store_true", help="檢驗所有題目")
  p_check.add_argument("--seed", type=int, default=42, help="隨機測資 Seed")
  p_check.add_argument(
      "--timeout", type=float, default=5.0, help="Solver 逾時秒數"
  )

  # 4. list 指令
  subparsers.add_parser("list", help="列出題庫所有題目與檔案建置狀態")

  # 5. generate 指令 (AI 模組)
  p_gen = subparsers.add_parser(
      "generate", help="使用 AI 協同生成 concept、題面或解答"
  )
  p_gen.add_argument("id", help="題目代號 (例如 DCA)")
  p_gen.add_argument("--prompt", default="", help="題目發想描述或構想文字")
  p_gen.add_argument(
      "--concept", action="store_true", help="僅生成 concept.yaml"
  )
  p_gen.add_argument(
      "--statement", action="store_true", help="僅生成 statement.md"
  )
  p_gen.add_argument("--solver", action="store_true", help="僅生成 solver.py")
  p_gen.add_argument(
      "--all",
      action="store_true",
      help="完整生成 (concept -> statement -> solver)",
  )
  p_gen.add_argument(
      "--ref", default="DBM,DAL", help="參考既有題目 ID 清單 (以逗號分隔)"
  )
  p_gen.add_argument("--api-key", default="", help="LLM API Key")
  p_gen.add_argument(
      "--provider",
      default="gemini",
      choices=["gemini", "openai"],
      help="AI 提供商 (預設 gemini)",
  )
  p_gen.add_argument("--model", default="", help="模型名稱")
  p_gen.add_argument(
      "--base-url", default="", help="OpenAI-compatible 自訂 Base URL"
  )

  args = parser.parse_args()

  if not args.command:
    parser.print_help()
    sys.exit(0)

  if args.command == "build":
    sys.exit(cmd_build(args))
  elif args.command == "preview":
    sys.exit(cmd_preview(args))
  elif args.command == "check":
    sys.exit(cmd_check(args))
  elif args.command == "list":
    sys.exit(cmd_list(args))
  elif args.command == "generate":
    sys.exit(cmd_generate(args))


if __name__ == "__main__":
  main()
