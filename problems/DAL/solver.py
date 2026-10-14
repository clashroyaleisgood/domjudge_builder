import random


def solver():
  t = int(input())  # 製作 1 份奶茶需要的紅茶公克數
  m = int(input())  # 製作 1 份奶茶需要的牛奶公克數
  x = int(input())  # 目前擁有的紅茶公克數
  y = int(input())  # 目前擁有的牛奶公克數

  # 最多可以製作幾份奶茶（基於紅茶量）
  portions = x / t

  # 總共需要的牛奶
  total_milk_needed = portions * m

  # 還需要準備多少公克的牛奶
  milk_needed = total_milk_needed - y

  print(portions)
  print(milk_needed)


def generate_inputs(seed=42) -> list[str]:
  rng = random.Random(seed)
  inputs = []
  for _ in range(8):
    t = rng.randint(1, 1000)
    m = rng.randint(1, 1000)
    x = rng.randint(1, 10**6)
    # 確保牛奶不足：y < (x/t) * m
    max_y = int((x / t) * m) - 1
    y = rng.randint(1, max(1, max_y))
    inputs.append(f"{t}\n{m}\n{x}\n{y}\n")
  return inputs


if __name__ == "__main__":
  solver()
