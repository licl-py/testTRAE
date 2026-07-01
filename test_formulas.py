import math
from typing import Tuple, Optional, Callable


# ============================================================
# 公式 0: 傅里叶级数 (Fourier Series)
# f(x) = a0 + Σ(n=1 to ∞) [an * cos(nπx/L) + bn * sin(nπx/L)]
# ============================================================

def fourier_series(
    x: float,
    a0: float,
    an: Callable[[int], float],
    bn: Callable[[int], float],
    L: float,
    terms: int = 20
) -> float:
    """
    计算傅里叶级数的前 N 项和。

    参数:
        x:     自变量
        a0:    常数项
        an:    余弦系数函数，入参 n 返回 a_n
        bn:    正弦系数函数，入参 n 返回 b_n
        L:     半周期长度
        terms: 求和的项数 (默认 20)
    """
    result = a0
    for n in range(1, terms + 1):
        result += an(n) * math.cos(n * math.pi * x / L)
        result += bn(n) * math.sin(n * math.pi * x / L)
    return result


# ============================================================
# 公式 1: 一元二次方程求根公式 (Quadratic Formula)
# x = (-b ± √(b² - 4ac)) / 2a
# ============================================================

def quadratic_formula(a: float, b: float, c: float) -> Tuple[Optional[float], Optional[float]]:
    """
    求解一元二次方程 ax^2 + bx + c = 0 的两个根。

    返回:
        (x1, x2) 两个根。如果判别式 < 0 则返回 (None, None) 表示无实数解。
    """
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return None, None

    sqrt_discriminant = math.sqrt(discriminant)
    x1 = (-b + sqrt_discriminant) / (2 * a)
    x2 = (-b - sqrt_discriminant) / (2 * a)
    return x1, x2


# ============================================================
# 测试代码
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("测试公式 0: 傅里叶级数")
    print("=" * 50)

    # 测试 1: 方波的傅里叶级数近似
    # f(x) ≈ Σ(n=1,3,5...) (4/πn) * sin(nπx/L)
    # 即 a0=0, an=0, bn = 4/(πn) (n为奇数), bn=0 (n为偶数), L=1
    L = 1.0

    def an_square_wave(n: int) -> float:
        return 0.0

    def bn_square_wave(n: int) -> float:
        return (4 / (math.pi * n)) if n % 2 == 1 else 0.0

    print("\n方波傅里叶级数近似 (a0=0, an=0, bn=4/(πn) 奇数项, L=1):")
    for x in [-0.5, 0.0, 0.25, 0.5]:
        val = fourier_series(x, 0.0, an_square_wave, bn_square_wave, L, terms=50)
        expected = 1 if 0 < x < L else (-1 if x < 0 else 0)
        print(f"  f({x:+.2f}) = {val:+.6f}  (预期符号: {'+' if val > 0 else '-'})")

    # 测试 2: 锯齿波
    # f(x) ≈ Σ(2/πn) * (-1)^(n+1) * sin(nπx)
    print("\n锯齿波傅里叶级数近似 (a0=0, an=0, bn=2*(-1)^(n+1)/(πn), L=1):")

    def bn_sawtooth(n: int) -> float:
        return 2 * ((-1) ** (n + 1)) / (math.pi * n)

    for x in [-0.5, 0.0, 0.25, 0.5]:
        val = fourier_series(x, 0.0, an_square_wave, bn_sawtooth, L, terms=50)
        print(f"  f({x:+.2f}) = {val:+.6f}")

    print("\n" + "=" * 50)
    print("测试公式 1: 一元二次方程求根公式")
    print("=" * 50)

    # 测试 1: 两个不同实根  x^2 - 5x + 6 = 0  =>  x=2, x=3
    a, b_val, c = 1, -5, 6
    x1, x2 = quadratic_formula(a, b_val, c)
    print(f"\n方程: {a}x^2 + {b_val}x + {c} = 0")
    print(f"  判别式 Δ = {b_val**2 - 4*a*c}")
    print(f"  x1 = {x1}, x2 = {x2}")
    print(f"  验证: a*x1^2+b*x1+c = {a*x1*x1 + b_val*x1 + c}")
    print(f"  验证: a*x2^2+b*x2+c = {a*x2*x2 + b_val*x2 + c}")

    # 测试 2: 重根  x^2 - 4x + 4 = 0  =>  x=2 (重根)
    a, b_val, c = 1, -4, 4
    x1, x2 = quadratic_formula(a, b_val, c)
    print(f"\n方程: {a}x^2 + {b_val}x + {c} = 0")
    print(f"  判别式 Δ = {b_val**2 - 4*a*c}")
    print(f"  x1 = {x1}, x2 = {x2}")
    assert abs(x1 - x2) < 1e-9, "重根应相等"

    # 测试 3: 无实数解  x^2 + x + 1 = 0  =>  判别式 < 0
    a, b_val, c = 1, 1, 1
    x1, x2 = quadratic_formula(a, b_val, c)
    print(f"\n方程: {a}x^2 + {b_val}x + {c} = 0")
    print(f"  判别式 Δ = {b_val**2 - 4*a*c} (< 0, 无实数解)")
    print(f"  结果: x1={x1}, x2={x2}")

    # 测试 4: 含小数系数 2x^2 + 3.5x - 1.2 = 0
    a, b_val, c = 2, 3.5, -1.2
    x1, x2 = quadratic_formula(a, b_val, c)
    print(f"\n方程: {a}x^2 + {b_val}x + {c} = 0")
    print(f"  判别式 Δ = {b_val**2 - 4*a*c:.4f}")
    print(f"  x1 = {x1:.6f}, x2 = {x2:.6f}")
    print(f"  验证: a*x1^2+b*x1+c = {a*x1*x1 + b_val*x1 + c:.2e}")
    print(f"  验证: a*x2^2+b*x2+c = {a*x2*x2 + b_val*x2 + c:.2e}")

    print("\n" + "=" * 50)
    print("所有测试完成！")
    print("=" * 50)