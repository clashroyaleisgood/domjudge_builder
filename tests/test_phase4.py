from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time
import urllib.request

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
  sys.path.insert(0, str(BASE_DIR))

from web.server import DomjudgeWebHandler

TEST_PORT = 8999
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"


def get(url_path):
  req = urllib.request.Request(f"{BASE_URL}{url_path}")
  with urllib.request.urlopen(req, timeout=10) as resp:
    return resp.status, resp.headers.get("Content-Type"), resp.read()


def post(url_path, json_data):
  body = json.dumps(json_data).encode("utf-8")
  req = urllib.request.Request(
      f"{BASE_URL}{url_path}",
      data=body,
      headers={"Content-Type": "application/json"},
  )
  with urllib.request.urlopen(req, timeout=15) as resp:
    return resp.status, json.loads(resp.read().decode("utf-8"))


def test_phase4_web():
  print("\n==========================================")
  print("開始執行 Phase 4 雙視圖 Web 工作台驗證測試...")
  print("==========================================")

  # 1. 啟動測試 Web 伺服器
  httpd = ThreadingHTTPServer(("127.0.0.1", TEST_PORT), DomjudgeWebHandler)
  server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
  server_thread.start()
  time.sleep(0.5)

  try:
    # 2. 測試靜態網頁載入
    status, ctype, body = get("/")
    assert status == 200, "首頁載入失敗"
    assert "DOMjudge Builder" in body.decode("utf-8")
    print(" [GET /] 首頁 HTML 載入測試通過！")

    status, ctype, body = get("/style.css")
    assert status == 200 and "css" in ctype
    print(" [GET /style.css] 靜態樣式載入測試通過！")

    status, ctype, body = get("/app.js")
    assert status == 200 and "javascript" in ctype
    print(" [GET /app.js] 前端腳本載入測試通過！")

    # 3. 測試 REST API: 題目清單
    status, ctype, raw = get("/api/problems")
    data = json.loads(raw.decode("utf-8"))
    assert data["success"] is True
    ids = [p["id"] for p in data["problems"]]
    assert "DBM" in ids and "DAL" in ids
    print(" [GET /api/problems] 題庫清單 API 測試通過！")

    # 4. 測試 REST API: 單題內容讀取
    status, ctype, raw = get("/api/problem/DBM")
    data = json.loads(raw.decode("utf-8"))
    assert data["success"] is True
    assert "statement" in data["data"] and "solver" in data["data"]
    print(" [GET /api/problem/DBM] 讀取單題內容 API 測試通過！")

    # 5. 測試 REST API: 執行驗證 Check
    status, data = post("/api/check", {"id": "DBM"})
    assert data["success"] is True
    assert data["result"]["samples_count"] == 2
    print(" [POST /api/check] 線上執行 Sanity Check 測試通過！")

    # 6. 測試 REST API: PDF 預覽與檔案串流
    status, data = post("/api/preview", {"id": "DBM"})
    assert data["success"] is True
    pdf_status, pdf_ctype, pdf_bytes = get("/api/pdf/DBM")
    assert pdf_status == 200 and "application/pdf" in pdf_ctype
    assert len(pdf_bytes) > 1000
    print(" [GET /api/pdf/DBM] 線上 PDF 即時渲染與串流測試通過！")

    # 7. 測試 REST API: 下載 DOMjudge ZIP
    zip_status, zip_ctype, zip_bytes = get("/api/download/DBM")
    assert zip_status == 200 and "application/zip" in zip_ctype
    assert len(zip_bytes) > 1000
    print(" [GET /api/download/DBM] DOMjudge ZIP 封包線上直接下載測試通過！")

    print("\n Phase 4 所有驗收條件全數通過！")

  finally:
    httpd.shutdown()
    httpd.server_close()


if __name__ == "__main__":
  test_phase4_web()
