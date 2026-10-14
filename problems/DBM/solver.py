import random


def solver():
  """標準解答邏輯：從 stdin 讀取材料與需求，計算並 print 至 stdout"""
  f = int(input())
  m = int(input())
  s = int(input())
  F = int(input())
  M = int(input())
  S = int(input())

  portions = min(F / f, M / m, S / s)
  remaining_f = F - portions * f
  remaining_m = M - portions * m
  remaining_s = S - portions * s

  print(portions)
  print(remaining_f)
  print(remaining_m)
  print(remaining_s)


def generate_inputs(seed=42) -> list[str]:
  """生成確定性隨機測資清單（不含題面公開範例）"""
  rng = random.Random(seed)
  inputs = []
  for _ in range(8):
    f = rng.randint(1, 1000)
    m = rng.randint(1, 1000)
    s = rng.randint(1, 1000)
    F = rng.randint(1, 10**6)
    M = rng.randint(1, 10**6)
    S = rng.randint(1, 10**6)
    inputs.append(f"{f}\n{m}\n{s}\n{F}\n{M}\n{S}\n")
  return inputs


if __name__ == "__main__":
  solver()
