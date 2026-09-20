"""
crop_circle_generator.py
=========================
Deterministic crop-circle generator based on Iterated Function Systems (IFS)
and the Collage Theorem.

Presets: rosette, rosette_dihedral, rings_spiral, fractal_tree, dragon,
         sierpinski (filled), prime_gap, prime_value, prime_residue.

Automatic point-count capping prevents MemoryError on high (n, depth).

Requires: numpy, matplotlib
Optional: scipy (for collage fitting)
"""

from __future__ import annotations

import os
import math
import cmath
import argparse
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection, LineCollection


# ============================================================
# 1. IFS CORE
# ============================================================

@dataclass
class Contraction:
    """
    Similarity contraction on the complex plane:

        w(z) = s * exp(i * theta) * z + t

    with 0 < s < 1.
    """
    s: float
    theta: float
    t: complex

    def __call__(self, z: complex) -> complex:
        return self.s * cmath.exp(1j * self.theta) * z + self.t

    def matrix(self) -> Tuple[np.ndarray, np.ndarray]:
        c, sn = math.cos(self.theta), math.sin(self.theta)
        M = self.s * np.array([[c, -sn], [sn, c]])
        b = np.array([self.t.real, self.t.imag])
        return M, b


@dataclass
class IFS:
    """A finite family of contractions."""
    maps: List[Contraction]

    @property
    def ratio(self) -> float:
        return max(w.s for w in self.maps)

    @property
    def n(self) -> int:
        return len(self.maps)

    def apply(self, K: np.ndarray) -> np.ndarray:
        pieces = []
        for w in self.maps:
            M, b = w.matrix()
            pieces.append((M @ K) + b[:, None])
        return np.concatenate(pieces, axis=1)

    def iterate(self, K0: np.ndarray, depth: int) -> np.ndarray:
        K = K0
        for _ in range(depth):
            K = self.apply(K)
        return K


# ============================================================
# 1b. SAFETY: POINT-COUNT CAP
# ============================================================

MAX_POINTS = 4_000_000


def effective_depth(n_maps: int, requested_depth: int,
                    cap: Optional[int] = None) -> int:
    if cap is None:
        cap = MAX_POINTS
    if n_maps <= 1:
        return requested_depth
    d = 0
    total = 1
    while d < requested_depth and total * n_maps <= cap:
        total *= n_maps
        d += 1
    return max(1, d)


# ============================================================
# 2. PATTERN LIBRARY
# ============================================================

def rosette_ifs(n: int, s: float = 1 / 3, r: float = 0.8) -> IFS:
    maps = []
    for k in range(n):
        theta = 2 * math.pi * k / n
        t = r * cmath.exp(1j * theta)
        maps.append(Contraction(s=s, theta=theta, t=t))
    return IFS(maps=maps)


def rosette_dihedral_ifs(n: int, s: float = 1 / 3, r: float = 0.8) -> IFS:
    maps = []
    for k in range(n):
        theta = 2 * math.pi * k / n
        rho = cmath.exp(1j * theta)
        maps.append(Contraction(s=s, theta=theta, t=r * rho))
        maps.append(Contraction(s=s, theta=-theta, t=r * rho))
    return IFS(maps=maps)


def ring_points(radii: Sequence[float], n_pts: int = 256) -> np.ndarray:
    pts = []
    for r in radii:
        for k in range(n_pts):
            th = 2 * math.pi * k / n_pts
            pts.append(complex(r * math.cos(th), r * math.sin(th)))
    return np.array([[p.real for p in pts], [p.imag for p in pts]])


def spiral_points(
    turns: float = 4.0,
    n_pts: int = 4000,
    growth: float = 0.02,
    initial_radius: float = 0.05,
) -> np.ndarray:
    thetas = np.linspace(0, 2 * math.pi * turns, n_pts)
    r = initial_radius * np.exp(growth * thetas)
    x = r * np.cos(thetas)
    y = r * np.sin(thetas)
    return np.vstack([x, y])


def tree_segments(
    x: float,
    y: float,
    angle: float,
    length: float,
    depth: int,
    branch_angle: float,
    shrink: float,
) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """
    Recursively generate binary tree line segments.
    Each call produces one segment (x,y) -> (x2,y2), then recurses on
    two children rotated by ±branch_angle and scaled by shrink.
    """
    if depth == 0:
        return []
    x2 = x + length * math.cos(angle)
    y2 = y + length * math.sin(angle)
    seg = ((x, y), (x2, y2))
    segs = [seg]
    segs.extend(tree_segments(x2, y2, angle + branch_angle,
                              length * shrink, depth - 1,
                              branch_angle, shrink))
    segs.extend(tree_segments(x2, y2, angle - branch_angle,
                              length * shrink, depth - 1,
                              branch_angle, shrink))
    return segs


def dragon_ifs() -> IFS:
    w1 = Contraction(s=1 / math.sqrt(2), theta=math.pi / 4, t=0)
    w2 = Contraction(s=1 / math.sqrt(2), theta=-3 * math.pi / 4, t=1 + 0j)
    return IFS(maps=[w1, w2])


def sierpinski_ifs() -> IFS:
    w1 = Contraction(s=0.5, theta=0.0, t=0 + 0j)
    w2 = Contraction(s=0.5, theta=0.0, t=0.5 + 0j)
    w3 = Contraction(s=0.5, theta=0.0, t=0.25 + 0.5j)
    return IFS(maps=[w1, w2, w3])


def sierpinski_triangles(
    depth: int,
    a: complex = 0 + 0j,
    b: complex = 1 + 0j,
    c: complex = 0.5 + (math.sqrt(3) / 2) * 1j,
) -> List[np.ndarray]:
    if depth == 0:
        return [np.array([[a.real, a.imag],
                          [b.real, b.imag],
                          [c.real, c.imag]])]
    mab = (a + b) / 2
    mbc = (b + c) / 2
    mca = (c + a) / 2
    out = []
    out.extend(sierpinski_triangles(depth - 1, a, mab, mca))
    out.extend(sierpinski_triangles(depth - 1, mab, b, mbc))
    out.extend(sierpinski_triangles(depth - 1, mca, mbc, c))
    return out


# ============================================================
# 3. SYMMETRY WRAPPER (for small point clouds only)
# ============================================================

def apply_dihedral(K: np.ndarray, n: int) -> np.ndarray:
    pieces = [K]
    for k in range(1, n):
        theta = 2 * math.pi * k / n
        c, s = math.cos(theta), math.sin(theta)
        R = np.array([[c, -s], [s, c]])
        pieces.append(R @ K)
    M = np.array([[1.0, 0.0], [0.0, -1.0]])
    reflected = M @ K
    pieces.append(reflected)
    for k in range(1, n):
        theta = 2 * math.pi * k / n
        c, s = math.cos(theta), math.sin(theta)
        R = np.array([[c, -s], [s, c]])
        pieces.append(R @ reflected)
    return np.concatenate(pieces, axis=1)


# ============================================================
# 4. PRIME-ENCODED VARIANT
# ============================================================

def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    for p in range(3, int(math.sqrt(n)) + 1, 2):
        if n % p == 0:
            return False
    return True


def prime_radial_pattern(
    n_primes: int = 400,
    max_radius: float = 1.0,
    mode: str = "gap",
) -> np.ndarray:
    primes = []
    x = 2
    while len(primes) < n_primes:
        if is_prime(x):
            primes.append(x)
        x += 1
    pts = []
    golden = math.pi * (3 - math.sqrt(5))
    max_gap = max(primes[k + 1] - primes[k] for k in range(len(primes) - 1))
    for i, p in enumerate(primes):
        if mode == "gap":
            gap = primes[i + 1] - primes[i] if i + 1 < len(primes) else max_gap
            r = max_radius * gap / max(1, max_gap)
            th = i * golden
        elif mode == "value":
            r = max_radius * math.sqrt(p) / math.sqrt(primes[-1])
            th = (p % 360) * math.pi / 180
        elif mode == "residue":
            q = 360
            r = max_radius * p / primes[-1]
            th = 2 * math.pi * (p % q) / q
        else:
            raise ValueError(f"unknown mode: {mode}")
        pts.append(complex(r * math.cos(th), r * math.sin(th)))
    return np.array([[p.real for p in pts], [p.imag for p in pts]])


# ============================================================
# 5. RENDERERS
# ============================================================

def _add_field_texture(ax, xmin, xmax, ymin, ymax,
                       n_dots: int = 25000,
                       color: str = "#e6e6c0") -> None:
    rng = np.random.default_rng(0)
    x = rng.uniform(xmin, xmax, n_dots)
    y = rng.uniform(ymin, ymax, n_dots)
    ax.scatter(x, y, s=0.2, c=color, alpha=0.45, linewidths=0, rasterized=True)


def plot_points_textured(
    K: np.ndarray,
    title: str = "Crop Circle",
    color: str = "#0d3d0d",
    marker_size: float = 6.0,
    alpha: float = 1.0,
    halo: bool = True,
    field: bool = True,
    save: Optional[str] = None,
    figsize: Tuple[float, float] = (10, 10),
    dpi: int = 300,
) -> None:
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=14, color="#222222", pad=12)

    xmin, xmax = K[0].min(), K[0].max()
    ymin, ymax = K[1].min(), K[1].max()
    pad = 0.05 * max(xmax - xmin, ymax - ymin, 1e-9)
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)

    if field:
        _add_field_texture(ax, xmin - pad, xmax + pad,
                           ymin - pad, ymax + pad)

    if halo:
        ax.scatter(K[0], K[1], s=marker_size * 4,
                   c=color, alpha=0.12, linewidths=0, rasterized=True)
        ax.scatter(K[0], K[1], s=marker_size * 2,
                   c=color, alpha=0.25, linewidths=0, rasterized=True)

    ax.scatter(K[0], K[1], s=marker_size,
               c=color, alpha=alpha, linewidths=0, rasterized=True)

    if save:
        fig.savefig(save, bbox_inches="tight", pad_inches=0.15, facecolor="white")
        print(f"saved: {save}")
    plt.close(fig)


def plot_filled_triangles(
    triangles: List[np.ndarray],
    title: str = "Sierpinski triangle",
    facecolor: str = "#0d3d0d",
    edgecolor: str = "#062006",
    edgewidth: float = 0.4,
    field: bool = True,
    save: Optional[str] = None,
    figsize: Tuple[float, float] = (10, 10),
    dpi: int = 300,
) -> None:
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=14, color="#222222", pad=12)

    all_pts = np.concatenate(triangles, axis=0)
    xmin, xmax = all_pts[:, 0].min(), all_pts[:, 0].max()
    ymin, ymax = all_pts[:, 1].min(), all_pts[:, 1].max()
    pad = 0.03 * max(xmax - xmin, ymax - ymin, 1e-9)
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)

    if field:
        _add_field_texture(ax, xmin - pad, xmax + pad,
                           ymin - pad, ymax + pad)

    coll = PolyCollection(
        triangles,
        facecolors=facecolor,
        edgecolors=edgecolor,
        linewidths=edgewidth,
    )
    ax.add_collection(coll)

    if save:
        fig.savefig(save, bbox_inches="tight", pad_inches=0.15, facecolor="white")
        print(f"saved: {save}")
    plt.close(fig)


def plot_rings_and_spiral(
    rings: np.ndarray,
    spiral: np.ndarray,
    title: str = "Rings + Spiral",
    ring_color: str = "#0d3d0d",
    spiral_color: str = "#062006",
    save: Optional[str] = None,
    figsize: Tuple[float, float] = (10, 10),
    dpi: int = 300,
) -> None:
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=14, color="#222222", pad=12)

    allx = np.concatenate([rings[0], spiral[0]])
    ally = np.concatenate([rings[1], spiral[1]])
    xmin, xmax = allx.min(), allx.max()
    ymin, ymax = ally.min(), ally.max()
    pad = 0.05 * max(xmax - xmin, ymax - ymin, 1e-9)
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)

    _add_field_texture(ax, xmin - pad, xmax + pad, ymin - pad, ymax + pad)

    ax.scatter(rings[0], rings[1], s=6.0,
               c=ring_color, alpha=1.0, linewidths=0, rasterized=True)
    ax.plot(spiral[0], spiral[1], color=spiral_color,
            linewidth=1.2, alpha=1.0, solid_capstyle="round")

    if save:
        fig.savefig(save, bbox_inches="tight", pad_inches=0.15, facecolor="white")
        print(f"saved: {save}")
    plt.close(fig)


def plot_tree_segments(
    segments: List[Tuple[Tuple[float, float], Tuple[float, float]]],
    title: str = "Fractal tree",
    color: str = "#0d3d0d",
    linewidth: float = 1.0,
    field: bool = True,
    save: Optional[str] = None,
    figsize: Tuple[float, float] = (10, 10),
    dpi: int = 300,
) -> None:
    """Render a list of line segments as a tree."""
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=14, color="#222222", pad=12)

    all_pts = np.array(segments).reshape(-1, 2)
    xmin, xmax = all_pts[:, 0].min(), all_pts[:, 0].max()
    ymin, ymax = all_pts[:, 1].min(), all_pts[:, 1].max()
    pad = 0.05 * max(xmax - xmin, ymax - ymin, 1e-9)
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)

    if field:
        _add_field_texture(ax, xmin - pad, xmax + pad,
                           ymin - pad, ymax + pad)

    coll = LineCollection(
        segments,
        colors=color,
        linewidths=linewidth,
        capstyle="round",
    )
    ax.add_collection(coll)

    if save:
        fig.savefig(save, bbox_inches="tight", pad_inches=0.15, facecolor="white")
        print(f"saved: {save}")
    plt.close(fig)


# ============================================================
# 6. HIGH-LEVEL PRESETS
# ============================================================

def preset_rosette(n: int = 12, depth: int = 6,
                   save: str = "rosette.png") -> None:
    F = rosette_ifs(n=n, s=1 / 3, r=0.8)
    d = effective_depth(F.n, depth)
    if d < depth:
        print(f"      [cap] rosette depth {depth} -> {d} "
              f"(n_maps={F.n}, cap={MAX_POINTS})")
    K = F.iterate(np.array([[1.0], [0.0]]), depth=d)
    plot_points_textured(
        K, title=f"Rosette IFS  n={n}  depth={d}",
        color="#0d3d0d", marker_size=4.5, alpha=1.0, save=save,
    )


def preset_rosette_dihedral(n: int = 12, depth: int = 6,
                            save: str = "rosette_dihedral.png") -> None:
    F = rosette_dihedral_ifs(n=n, s=1 / 3, r=0.8)
    d = effective_depth(F.n, depth)
    if d < depth:
        print(f"      [cap] dihedral depth {depth} -> {d} "
              f"(n_maps={F.n}, cap={MAX_POINTS})")
    K = F.iterate(np.array([[1.0], [0.0]]), depth=d)
    plot_points_textured(
        K, title=f"Dihedral rosette  D_{n}  depth={d}",
        color="#062e06", marker_size=2.5, alpha=1.0, save=save,
    )


def preset_rings_spiral(save: str = "rings_spiral.png") -> None:
    rings = ring_points([0.2, 0.35, 0.5, 0.65, 0.8, 0.95], n_pts=256)
    spiral = spiral_points(turns=4.0, n_pts=4000,
                           growth=0.02, initial_radius=0.05)
    plot_rings_and_spiral(rings, spiral,
                          title="Concentric rings + logarithmic spiral",
                          save=save)


def preset_fractal_tree(depth: int = 12, save: str = "fractal_tree.png") -> None:
    """Binary fractal tree (line segments, recursive)."""
    # Cap depth: 2^depth segments. depth 14 -> 16384, safe.
    d = min(depth, 15)
    if d < depth:
        print(f"      [cap] tree depth {depth} -> {d}")
    branch_angle = math.pi / 7      # ~25.7 degrees
    shrink = 0.72
    segments = tree_segments(
        x=0.0, y=0.0, angle=math.pi / 2,
        length=1.0, depth=d,
        branch_angle=branch_angle, shrink=shrink,
    )
    plot_tree_segments(
        segments,
        title=f"Fractal tree  depth={d}  segments={len(segments)}",
        color="#0d3d0d",
        linewidth=0.9,
        save=save,
    )


def preset_dragon(depth: int = 16, save: str = "dragon.png") -> None:
    F = dragon_ifs()
    d = effective_depth(F.n, depth)
    if d < depth:
        print(f"      [cap] dragon depth {depth} -> {d}")
    K = F.iterate(np.array([[0.0], [0.0]]), depth=d)
    plot_points_textured(
        K, title=f"Heighway dragon IFS  depth={d}",
        color="#0d3d0d", marker_size=3.0, alpha=1.0, save=save,
    )


def preset_sierpinski(depth: int = 8, save: str = "sierpinski.png",
                      filled: bool = True) -> None:
    if filled:
        d = min(depth, 10)
        if d < depth:
            print(f"      [cap] sierpinski depth {depth} -> {d}")
        tris = sierpinski_triangles(depth=d)
        plot_filled_triangles(
            tris,
            title=f"Sierpinski triangle  (filled, depth={d})",
            facecolor="#0d3d0d",
            edgecolor="#062006",
            edgewidth=0.4,
            save=save,
        )
    else:
        F = sierpinski_ifs()
        d = effective_depth(F.n, depth)
        if d < depth:
            print(f"      [cap] sierpinski depth {depth} -> {d}")
        K = F.iterate(np.array([[0.0], [0.0]]), depth=d)
        plot_points_textured(
            K, title=f"Sierpinski IFS  depth={d}",
            color="#0d3d0d", marker_size=8.0, alpha=1.0, save=save,
        )


def preset_prime_pattern(n_primes: int = 400, mode: str = "gap",
                         n_folds: int = 12,
                         save: str = "prime_pattern.png") -> None:
    K = prime_radial_pattern(n_primes=n_primes, mode=mode)
    n_pts_total = 2 * n_folds * K.shape[1]
    if n_pts_total <= MAX_POINTS:
        K = apply_dihedral(K, n=n_folds)
    else:
        print(f"      [cap] prime dihedral skipped "
              f"({n_pts_total} > {MAX_POINTS})")
    plot_points_textured(
        K, title=f"Prime-encoded pattern  mode={mode}  D_{n_folds}",
        color="#062e06", marker_size=25.0, alpha=1.0, save=save,
    )


# ============================================================
# 7. COLLAGE FITTING (optional, requires scipy)
# ============================================================

def collage_fit(target: np.ndarray, n_maps: int, s_cap: float = 0.5) -> IFS:
    from scipy.cluster.vq import kmeans2
    from scipy.linalg import svd

    centroids, labels = kmeans2(target.T, n_maps, minit="++", seed=42)
    maps = []
    for i in range(n_maps):
        cluster = target[:, labels == i]
        if cluster.shape[1] < 2:
            continue
        c_src = cluster.mean(axis=1)
        c_dst = centroids[i]
        X = cluster - c_src[:, None]
        U, S, _ = svd(X, full_matrices=False)
        s_fit = min(s_cap, 0.9 * S[1] / S[0]) if S[0] > 1e-9 else s_cap
        theta = math.atan2(U[1, 0], U[0, 0])
        rot = s_fit * cmath.exp(1j * theta)
        t = complex(c_dst[0], c_dst[1]) - rot * complex(c_src[0], c_src[1])
        maps.append(Contraction(s=s_fit, theta=theta, t=t))
    return IFS(maps=maps)


# ============================================================
# 8. CLI
# ============================================================

def main() -> None:
    global MAX_POINTS

    parser = argparse.ArgumentParser(
        description="Deterministic crop-circle generator via IFS + Collage."
    )
    parser.add_argument(
        "--preset",
        choices=[
            "rosette", "rosette_dihedral", "rings_spiral",
            "fractal_tree", "dragon", "sierpinski",
            "prime_gap", "prime_value", "prime_residue", "all",
        ],
        default="all",
    )
    parser.add_argument("--n", type=int, default=12, help="symmetry order")
    parser.add_argument("--depth", type=int, default=6, help="iteration depth")
    parser.add_argument("--outdir", type=str, default="output",
                        help="output directory")
    parser.add_argument("--max-points", type=int, default=MAX_POINTS,
                        help="point-count cap (default 4M)")
    args = parser.parse_args()

    MAX_POINTS = args.max_points

    od = args.outdir.rstrip("/\\") or "output"
    os.makedirs(od, exist_ok=True)

    def path(name: str) -> str:
        return os.path.join(od, name)

    jobs = {
        "rosette": lambda: preset_rosette(
            n=args.n, depth=args.depth, save=path("rosette.png")),
        "rosette_dihedral": lambda: preset_rosette_dihedral(
            n=args.n, depth=args.depth, save=path("rosette_dihedral.png")),
        "rings_spiral": lambda: preset_rings_spiral(
            save=path("rings_spiral.png")),
        "fractal_tree": lambda: preset_fractal_tree(
            depth=args.depth + 6, save=path("fractal_tree.png")),
        "dragon": lambda: preset_dragon(
            depth=args.depth + 10, save=path("dragon.png")),
        "sierpinski": lambda: preset_sierpinski(
            depth=args.depth + 2, save=path("sierpinski.png"), filled=True),
        "prime_gap": lambda: preset_prime_pattern(
            n_primes=400, mode="gap", n_folds=args.n, save=path("prime_gap.png")),
        "prime_value": lambda: preset_prime_pattern(
            n_primes=400, mode="value", n_folds=args.n, save=path("prime_value.png")),
        "prime_residue": lambda: preset_prime_pattern(
            n_primes=400, mode="residue", n_folds=args.n, save=path("prime_residue.png")),
    }

    if args.preset == "all":
        for name, job in jobs.items():
            print(f"generating: {name}")
            job()
    else:
        jobs[args.preset]()

    print("\nDone.")


if __name__ == "__main__":
    main()