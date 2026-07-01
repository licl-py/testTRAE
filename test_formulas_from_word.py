"""
自动生成的公式测试代码 - 从 Word 文档中提取的公式
"""
import math
from typing import Tuple, Optional, Callable


# ============================================================
# 公式 1: 一元二次方程求根公式 (Quadratic Formula)
# 提取文本: x=(-b±√(b^2-4ac))/(2a)
# 原始形式: x = (-b ± √(b² - 4ac)) / 2a
# ============================================================

def quadratic_formula(a: float, b: float, c: float) -> Tuple[Optional[float], Optional[float]]:
    """
    求解一元二次方程 ax^2 + bx + c = 0 的两个根。
    公式: x = (-b ± √(b² - 4ac)) / 2a
    
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
# 公式 2: 傅里叶级数 (Fourier Series)
# 提取文本: fx=a_0+∑_n=1^∞(a_ncos((nπx)/(L))+b_nsin((nπx)/(L)))
# 原始形式: f(x) = a₀ + Σ[n=1→∞] (aₙcos(nπx/L) + bₙsin(nπx/L))
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
    公式: f(x) = a₀ + Σ[n=1→∞] (aₙcos(nπx/L) + bₙsin(nπx/L))
    
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
# 测试代码
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("公式测试 - 从 Word 文档自动提取")
    print("=" * 60)
    
    # --- 测试公式 1: 一元二次方程求根公式 ---
    print("\n" + "=" * 60)
    print("测试公式 1: 一元二次方程求根公式")
    print("公式: x = (-b ± √(b² - 4ac)) / 2a")
    print("=" * 60)
    
    test_cases = [
        (1, -5, 6, "两个不同实根"),
        (1, -4, 4, "重根"),
        (1, 1, 1, "无实数解"),
        (2, 3.5, -1.2, "含小数系数"),
    ]
    
    for a, b, c, desc in test_cases:
        x1, x2 = quadratic_formula(a, b, c)
        print(f"\n方程: {a}x² + {b}x + {c} = 0  ({desc})")
        discriminant = b*b - 4*a*c
        print(f"  判别式 Δ = {discriminant:.4f}")
        if x1 is None:
            print(f"  结果: 无实数解 ✓")
        else:
            print(f"  x1 = {x1:.6f}, x2 = {x2:.6f}")
            verify1 = a*x1*x1 + b*x1 + c
            verify2 = a*x2*x2 + b*x2 + c
            print(f"  验证: a*x1²+b*x1+c = {verify1:.2e} ✓")
            print(f"  验证: a*x2²+b*x2+c = {verify2:.2e} ✓")
    
    # --- 测试公式 2: 傅里叶级数 ---
    print("\n" + "=" * 60)
    print("测试公式 2: 傅里叶级数")
    print("公式: f(x) = a₀ + Σ(aₙcos(nπx/L) + bₙsin(nπx/L))")
    print("=" * 60)
    
    L = 1.0
    
    # 方波近似
    def an_square(n: int) -> float:
        return 0.0
    
    def bn_square(n: int) -> float:
        return (4 / (math.pi * n)) if n % 2 == 1 else 0.0
    
    print("\n方波傅里叶级数近似 (前50项):")
    for x in [-0.5, 0.0, 0.25, 0.5]:
        val = fourier_series(x, 0.0, an_square, bn_square, L, terms=50)
        expected_sign = '+' if x > 0 else ('-' if x < 0 else '0')
        print(f"  f({x:+.2f}) = {val:+.6f} (预期符号: {expected_sign})")
    
    # 锯齿波近似
    def bn_sawtooth(n: int) -> float:
        return 2 * ((-1) ** (n + 1)) / (math.pi * n)
    
    print("\n锯齿波傅里叶级数近似 (前50项):")
    for x in [-0.5, 0.0, 0.25, 0.5]:
        val = fourier_series(x, 0.0, an_square, bn_sawtooth, L, terms=50)
        print(f"  f({x:+.2f}) = {val:+.6f}")
    
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)
