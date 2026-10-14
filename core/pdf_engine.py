import os
from pathlib import Path
import subprocess
import tempfile


def find_edge_path() -> str:
  """搜尋本機系統中的 Microsoft Edge 執行路徑"""
  candidates = [
      r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
      r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
      os.path.expandvars(
          r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"
      ),
  ]
  for path in candidates:
    if os.path.exists(path):
      return path
  return ""


def compile_html_to_pdf(
    html_content: str, output_pdf_path: Path | str, edge_path: str = ""
) -> Path:
  """使用 Edge Headless 將 HTML 編譯為符合 A4 印刷格式的 PDF。"""
  exe = edge_path or find_edge_path()
  if not exe or not os.path.exists(exe):
    raise FileNotFoundError(
        "系統中找不到 Microsoft Edge 執行檔 (msedge.exe)，無法轉換 PDF。"
    )

  output_pdf = Path(output_pdf_path).resolve()
  output_pdf.parent.mkdir(parents=True, exist_ok=True)

  # 寫入臨時 HTML
  tmp_fd, tmp_html_path = tempfile.mkstemp(suffix=".html")
  try:
    with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
      f.write(html_content)

    file_url = "file:///" + tmp_html_path.replace("\\", "/")

    cmd = [
        exe,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=2000",
        f"--print-to-pdf={str(output_pdf)}",
        file_url,
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if not output_pdf.exists() or output_pdf.stat().st_size == 0:
      raise RuntimeError(
          f"Edge 輸出 PDF 失敗 (code {res.returncode}): {res.stderr}"
      )

  finally:
    if os.path.exists(tmp_html_path):
      try:
        os.remove(tmp_html_path)
      except OSError:
        pass

  return output_pdf
