import json
import os
import re
import urllib.error
import urllib.request


class LLMClient:
  """輕量化 LLM 客戶端：使用 Python 標準庫 urllib，零外部 SDK 依賴。

  支援 Gemini 與 OpenAI 兼容格式 (含 DeepSeek, OpenRouter, Ollama)。
  """

  def __init__(
      self,
      api_key: str = "",
      provider: str = "gemini",
      model: str = "",
      base_url: str = "",
  ):
    self.api_key = (
        api_key
        or os.environ.get("DOMJUDGE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    )
    self.provider = provider.lower()
    self.base_url = base_url.rstrip("/")
    self.is_mock = (
        self.api_key == "mock" or os.environ.get("DOMJUDGE_MOCK_AI") == "1"
    )

    if not model:
      self.model = (
          "gemini-1.5-flash" if self.provider == "gemini" else "gpt-4o-mini"
      )
    else:
      self.model = model

  def generate(self, prompt: str, system_prompt: str = "") -> str:
    """發送請求並取得模型純文字回應"""
    if self.is_mock:
      return self._mock_response(prompt)

    if not self.api_key:
      raise ValueError(
          "未提供 API Key！請透過參數傳入或設定環境變數 DOMJUDGE_API_KEY /"
          " GEMINI_API_KEY / OPENAI_API_KEY。"
      )

    if self.provider == "gemini":
      return self._call_gemini(prompt, system_prompt)
    else:
      return self._call_openai(prompt, system_prompt)

  def _call_gemini(self, prompt: str, system_prompt: str = "") -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
    full_prompt = (
        f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    ).strip()

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )

    try:
      with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        text = res["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip()
    except urllib.error.HTTPError as e:
      err_body = e.read().decode("utf-8", errors="replace")
      raise RuntimeError(f"Gemini API 呼叫失敗 (HTTP {e.code}): {err_body}") from e

  def _call_openai(self, prompt: str, system_prompt: str = "") -> str:
    endpoint = self.base_url or "https://api.openai.com/v1"
    url = f"{endpoint}/chat/completions"

    messages = []
    if system_prompt:
      messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": self.model,
        "messages": messages,
        "temperature": 0.2,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {self.api_key}",
    }
    req = urllib.request.Request(url, data=data, headers=headers)

    try:
      with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        text = res["choices"][0]["message"]["content"]
        return text.strip()
    except urllib.error.HTTPError as e:
      err_body = e.read().decode("utf-8", errors="replace")
      raise RuntimeError(f"OpenAI API 呼叫失敗 (HTTP {e.code}): {err_body}") from e

  def _mock_response(self, prompt: str) -> str:
    """供自動化單元測試使用的確定性 Mock 模擬器"""
    if "【任務一：生成 concept.yaml】" in prompt:
      return """id: DCA
title: 計算披薩切片與剩餘角度
timelimit: 1.0
memory: 64
samples: 2
validator_flags: 'float_tolerance 1E-3'

concept:
  story_theme: "聚會平分披薩"
  core_algorithm: "整數除法與餘數計算"
  description: "計算給定人數與披薩切片時，每人分得片數與剩餘片數。"
"""
    elif "【任務二：生成 statement.md】" in prompt:
      return """---
id: DCA
title: 計算披薩切片與剩餘角度
timelimit: 1.0
memory: 64
samples: 2
validator_flags: 'float_tolerance 1E-3'
---

# DCA - 計算披薩切片與剩餘角度

### 題目敘述

小明買了披薩想要跟朋友們平分。
給定披薩總切片數 $S$ 與聚會人數 $P$，請計算每個人最多可以分得幾片披薩，以及最後會剩下幾片披薩。

### 輸入說明

第一行包含一個整數 $S\ (1 \\le S \\le 10^6)$，代表披薩總切片數。
第二行包含一個整數 $P\ (1 \\le P \\le 1000)$，代表聚會人數。

### 輸出說明

第一行輸出每個人分得的披薩片數。
第二行輸出最後剩下的披薩片數。

### 範例輸入 #1

```
10
3
```

### 範例輸出 #1

```
3
1
```

### 範例說明 #1

10 片披薩分給 3 個人，每人分得 3 片 ($3 \\times 3 = 9$)，剩下 1 片。

### 範例輸入 #2

```
20
5
```

### 範例輸出 #2

```
4
0
```

### 範例說明 #2

20 片披薩分給 5 個人，剛好每人分得 4 片，剩下 0 片。

### 測試資訊

記憶體限制：64MB
時間限制：1s
"""
    elif "【任務三：生成 solver.py】" in prompt:
      return """import random

def solver():
    S = int(input())
    P = int(input())
    print(S // P)
    print(S % P)

def generate_inputs(seed=42) -> list[str]:
    rng = random.Random(seed)
    inputs = []
    for _ in range(8):
      S = rng.randint(1, 10**6)
      P = rng.randint(1, 1000)
      inputs.append(f"{S}\\n{P}\\n")
    return inputs

if __name__ == "__main__":
    solver()
"""
    return "Mock response"
