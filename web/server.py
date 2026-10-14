from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse

# 確保專案根目錄在 sys.path 中
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
  sys.path.insert(0, str(BASE_DIR))

from ai.client import LLMClient
from ai.generator import (
    generate_concept_file,
    generate_solver_file,
    generate_statement_file,
)
from core.builder import (
    build_problem,
    check_problem,
    discover_problems,
    preview_problem,
)
from core.spec import load_spec

STATIC_DIR = BASE_DIR / "web" / "static"
PROBLEMS_DIR = BASE_DIR / "problems"
DIST_DIR = BASE_DIR / "dist"


class DomjudgeWebHandler(BaseHTTPRequestHandler):
  """輕量 REST API 與靜態檔案伺服處理器 (純標準庫實作，零依賴)"""

  def _send_json(self, data, status=200):
    content = json.dumps(data, ensure_ascii=False).encode("utf-8")
    self.send_response(status)
    self.send_header("Content-Type", "application/json; charset=utf-8")
    self.send_header("Content-Length", str(len(content)))
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    self.wfile.write(content)

  def _send_error_json(self, msg, status=400):
    self._send_json({"success": False, "error": str(msg)}, status=status)

  def _read_json_body(self):
    content_len = int(self.headers.get("Content-Length", 0))
    if content_len == 0:
      return {}
    raw_body = self.rfile.read(content_len).decode("utf-8")
    return json.loads(raw_body)

  def do_GET(self):
    parsed = urlparse(self.path)
    path = parsed.path

    # API: 列出所有題目與狀態
    if path == "/api/problems":
      problems = []
      for p_dir in discover_problems(PROBLEMS_DIR):
        pid = p_dir.name
        title = pid
        try:
          spec = load_spec(p_dir)
          title = spec.title
          limits = {
              "timelimit": spec.timelimit,
              "memory": spec.memory,
              "samples": spec.samples,
              "flags": spec.validator_flags,
          }
        except Exception:
          limits = {}

        problems.append({
            "id": pid,
            "title": title,
            "limits": limits,
            "has_concept": (p_dir / "concept.yaml").exists(),
            "has_statement": (p_dir / "statement.md").exists(),
            "has_solver": (p_dir / "solver.py").exists(),
            "has_pdf": (p_dir / "problem.pdf").exists(),
            "has_zip": (DIST_DIR / f"{pid}.zip").exists(),
        })
      return self._send_json({"success": True, "problems": problems})

    # API: 取得單一題目原始檔案內容
    elif path.startswith("/api/problem/"):
      pid = path.split("/")[3]
      p_dir = PROBLEMS_DIR / pid
      if not p_dir.is_dir():
        return self._send_error_json(f"找不到題目 {pid}", 404)

      data = {
          "id": pid,
          "concept": (
              (p_dir / "concept.yaml").read_text("utf-8")
              if (p_dir / "concept.yaml").exists()
              else ""
          ),
          "statement": (
              (p_dir / "statement.md").read_text("utf-8")
              if (p_dir / "statement.md").exists()
              else ""
          ),
          "solver": (
              (p_dir / "solver.py").read_text("utf-8")
              if (p_dir / "solver.py").exists()
              else ""
          ),
          "has_pdf": (p_dir / "problem.pdf").exists(),
          "has_zip": (DIST_DIR / f"{pid}.zip").exists(),
      }
      return self._send_json({"success": True, "data": data})

    # API: 取得 PDF 串流直接預覽
    elif path.startswith("/api/pdf/"):
      pid = path.split("/")[3]
      pdf_path = PROBLEMS_DIR / pid / "problem.pdf"
      if not pdf_path.exists():
        return self._send_error_json("PDF 尚未編譯", 404)

      content = pdf_path.read_bytes()
      self.send_response(200)
      self.send_header("Content-Type", "application/pdf")
      self.send_header("Content-Length", str(len(content)))
      self.send_header("Content-Disposition", f"inline; filename={pid}.pdf")
      self.end_headers()
      return self.wfile.write(content)

    # API: 下載 DOMjudge ZIP 題目包
    elif path.startswith("/api/download/"):
      pid = path.split("/")[3]
      zip_path = DIST_DIR / f"{pid}.zip"
      if not zip_path.exists():
        return self._send_error_json("ZIP 尚未打包", 404)

      content = zip_path.read_bytes()
      self.send_response(200)
      self.send_header("Content-Type", "application/zip")
      self.send_header("Content-Length", str(len(content)))
      self.send_header("Content-Disposition", f"attachment; filename={pid}.zip")
      self.end_headers()
      return self.wfile.write(content)

    # 靜態資源路由
    else:
      clean_path = path.lstrip("/") or "index.html"
      file_path = STATIC_DIR / clean_path
      if not file_path.exists() or file_path.is_dir():
        file_path = STATIC_DIR / "index.html"

      if not file_path.exists():
        self.send_response(404)
        return self.end_headers()

      mime_type, _ = mimetypes.guess_type(str(file_path))
      mime_type = mime_type or "application/octet-stream"

      content = file_path.read_bytes()
      self.send_response(200)
      self.send_header("Content-Type", mime_type)
      self.send_header("Content-Length", str(len(content)))
      self.end_headers()
      self.wfile.write(content)

  def do_POST(self):
    parsed = urlparse(self.path)
    path = parsed.path

    try:
      body = self._read_json_body()

      # API: 儲存題目原始檔 (concept, statement, solver)
      if path == "/api/save":
        pid = body.get("id", "").strip().upper()
        if not pid:
          return self._send_error_json("未指定題目 ID")

        p_dir = PROBLEMS_DIR / pid
        p_dir.mkdir(parents=True, exist_ok=True)

        if "concept" in body and body["concept"] is not None:
          (p_dir / "concept.yaml").write_text(body["concept"], "utf-8")
        if "statement" in body and body["statement"] is not None:
          (p_dir / "statement.md").write_text(body["statement"], "utf-8")
        if "solver" in body and body["solver"] is not None:
          (p_dir / "solver.py").write_text(body["solver"], "utf-8")

        return self._send_json({"success": True, "message": f"題目 {pid} 已儲存"})

      # API: 執行格式檢查與 Sanity Check
      elif path == "/api/check":
        pid = body.get("id", "").strip().upper()
        p_dir = PROBLEMS_DIR / pid
        res = check_problem(
            p_dir,
            seed=int(body.get("seed", 42)),
            timeout=float(body.get("timeout", 5.0)),
        )
        return self._send_json({"success": True, "result": res})

      # API: 編譯 PDF 預覽
      elif path == "/api/preview":
        pid = body.get("id", "").strip().upper()
        p_dir = PROBLEMS_DIR / pid
        pdf_path = preview_problem(p_dir)
        return self._send_json({
            "success": True,
            "pdf_url": f"/api/pdf/{pid}?t={os.path.getmtime(pdf_path)}",
        })

      # API: 執行完整建置與打包 ZIP
      elif path == "/api/build":
        pid = body.get("id", "").strip().upper()
        p_dir = PROBLEMS_DIR / pid
        res = build_problem(
            problem_dir=p_dir,
            dist_dir=DIST_DIR,
            seed=int(body.get("seed", 42)),
            timeout=float(body.get("timeout", 5.0)),
        )
        return self._send_json({
            "success": True,
            "result": {
                "id": res["id"],
                "title": res["title"],
                "testcases_count": res["testcases_count"],
                "samples_count": res["samples_count"],
                "secret_count": res["secret_count"],
                "zip_download_url": f"/api/download/{pid}",
                "pdf_url": f"/api/pdf/{pid}",
            },
        })

      # API: AI 協同生成 (發想 / 題本 / 解答)
      elif path == "/api/generate":
        pid = body.get("id", "").strip().upper()
        step = body.get("step", "concept")  # concept, statement, solver
        prompt = body.get("prompt", "")
        refs = body.get("refs", [])
        api_key = body.get("api_key", "")
        provider = body.get("provider", "gemini")
        model = body.get("model", "")
        base_url = body.get("base_url", "")

        client = LLMClient(
            api_key=api_key, provider=provider, model=model, base_url=base_url
        )

        p_dir = PROBLEMS_DIR / pid
        p_dir.mkdir(parents=True, exist_ok=True)

        if step == "concept":
          generate_concept_file(
              pid, prompt, ref_ids=refs, client=client, problems_dir=PROBLEMS_DIR
          )
          content = (p_dir / "concept.yaml").read_text("utf-8")
          return self._send_json({
              "success": True,
              "step": "concept",
              "content": content,
          })

        elif step == "statement":
          ref_id = refs[0] if refs else "DBM"
          generate_statement_file(
              pid, client=client, problems_dir=PROBLEMS_DIR, ref_id=ref_id
          )
          content = (p_dir / "statement.md").read_text("utf-8")
          return self._send_json({
              "success": True,
              "step": "statement",
              "content": content,
          })

        elif step == "solver":
          ref_id = refs[0] if refs else "DBM"
          generate_solver_file(
              pid, client=client, problems_dir=PROBLEMS_DIR, ref_id=ref_id
          )
          content = (p_dir / "solver.py").read_text("utf-8")
          return self._send_json({
              "success": True,
              "step": "solver",
              "content": content,
          })

        else:
          return self._send_error_json(f"未知生成步驟: {step}")

      else:
        return self._send_error_json("無效的 API 端點", 404)

    except Exception as e:
      return self._send_error_json(str(e), 500)

  def log_message(self, format, *args):
    # 簡化請求 log，避免雜訊
    sys.stdout.write(f"[HTTP] {self.address_string()} - {args[0]}\n")


def run_server(host: str = "127.0.0.1", port: int = 8000):
  """啟動 Web 服務"""
  server_address = (host, port)
  httpd = ThreadingHTTPServer(server_address, DomjudgeWebHandler)
  print(f"\n[SERVER] DOMjudge Builder Web 工作台已啟動！")
  print(f"[SERVER] 本機訪問網址: http://{host}:{port}")
  print(f"[SERVER] 按 Ctrl + C 可終止服務。\n")
  try:
    httpd.serve_forever()
  except KeyboardInterrupt:
    print("\n[SERVER] 正在關閉 Web 伺服器...")
    httpd.server_close()


if __name__ == "__main__":
  run_server()
