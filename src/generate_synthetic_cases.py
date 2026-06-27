import json
import math
import random
from pathlib import Path


def write_case(path, name, description, die, terminal_size, spacing, positions, nets):
    payload = {
        "name": name,
        "description": description,
        "die": list(die),
        "terminal_size": list(terminal_size),
        "terminal_spacing": spacing,
        "positions": [[int(x), int(y)] for x, y in positions],
        "nets": nets,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def clustered_positions(n, die, terminal_size, spacing, clusters, jitter, seed):
    rng = random.Random(seed)
    lx, ly, hx, hy = die
    w, h = terminal_size
    centers = []
    cols = math.ceil(math.sqrt(clusters))
    rows = math.ceil(clusters / cols)
    for i in range(clusters):
        col = i % cols
        row = i // cols
        cx = lx + (col + 0.5) * (hx - lx) / cols
        cy = ly + (row + 0.5) * (hy - ly) / rows
        centers.append((cx, cy))

    positions = []
    for i in range(n):
        cx, cy = centers[i % clusters]
        x = cx + rng.randint(-jitter, jitter)
        y = cy + rng.randint(-jitter, jitter)
        x = max(lx, min(hx - w - spacing, x))
        y = max(ly, min(hy - h - spacing, y))
        positions.append((x, y))
    return positions


def diagonal_pressure_positions(n, die, terminal_size, spacing, seed):
    rng = random.Random(seed)
    lx, ly, hx, hy = die
    w, h = terminal_size
    positions = []
    usable_w = hx - lx - w - spacing
    usable_h = hy - ly - h - spacing
    for i in range(n):
        t = i / max(1, n - 1)
        x = lx + 0.12 * usable_w + t * 0.62 * usable_w
        y = ly + 0.15 * usable_h + t * 0.55 * usable_h
        x += rng.randint(-spacing, spacing)
        y += rng.randint(-spacing, spacing)
        positions.append((x, y))
    return positions


def local_nets(positions, seed, min_fanout=2, max_fanout=4):
    rng = random.Random(seed)
    order = sorted(range(len(positions)), key=lambda i: (positions[i][0] + positions[i][1], positions[i][0]))
    nets = []
    cursor = 0
    while cursor < len(order):
        fanout = rng.randint(min_fanout, max_fanout)
        net = order[cursor:cursor + fanout]
        if len(net) >= 2:
            nets.append(net)
        cursor += fanout

    stride = max(8, len(order) // 80)
    for start in range(0, len(order) - stride, stride * 3):
        net = [order[start], order[start + stride // 2], order[start + stride]]
        nets.append(net)
    return nets


def main():
    out_dir = Path(__file__).resolve().parents[1] / "benchmark" / "synthetic"
    out_dir.mkdir(parents=True, exist_ok=True)

    positions = clustered_positions(
        n=300,
        die=(0, 0, 3600, 2400),
        terminal_size=(24, 24),
        spacing=12,
        clusters=120,
        jitter=18,
        seed=300,
    )
    write_case(
        out_dir / "large_sparse_300.json",
        "large_sparse_300",
        "A larger sparse case with mild clusters and enough whitespace.",
        die=(0, 0, 3600, 2400),
        terminal_size=(24, 24),
        spacing=12,
        positions=positions,
        nets=local_nets(positions, seed=1300),
    )

    positions = clustered_positions(
        n=800,
        die=(0, 0, 5200, 3600),
        terminal_size=(28, 28),
        spacing=14,
        clusters=140,
        jitter=24,
        seed=800,
    )
    write_case(
        out_dir / "large_medium_800.json",
        "large_medium_800",
        "A medium-density clustered case with many local overlaps.",
        die=(0, 0, 5200, 3600),
        terminal_size=(28, 28),
        spacing=14,
        positions=positions,
        nets=local_nets(positions, seed=1800),
    )

    positions = diagonal_pressure_positions(
        n=1500,
        die=(0, 0, 7200, 5200),
        terminal_size=(30, 30),
        spacing=15,
        seed=1500,
    )
    write_case(
        out_dir / "large_dense_1500.json",
        "large_dense_1500",
        "A large dense diagonal pressure case that stresses displacement.",
        die=(0, 0, 7200, 5200),
        terminal_size=(30, 30),
        spacing=15,
        positions=positions,
        nets=local_nets(positions, seed=2500),
    )


if __name__ == "__main__":
    main()
