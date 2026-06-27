import argparse
import contextlib
import io
import json
from pathlib import Path

import dplacer_horizon
import Die
import Terminal
from Legalization import Legalization


def load_case(path):
    with open(path, "r", encoding="utf-8") as f:
        case = json.load(f)

    required = ["die", "terminal_size", "terminal_spacing", "positions"]
    missing = [key for key in required if key not in case]
    if missing:
        raise ValueError(f"{path} is missing required fields: {', '.join(missing)}")
    return case


def make_inputs(case):
    die = Die.Die()
    die.setDieSize(*case["die"])

    terminals = Terminal.Terminals()
    terminal_w, terminal_h = case["terminal_size"]
    terminals.setTerminalSize(terminal_w, terminal_h)
    terminals.setTerminalSpacing(case["terminal_spacing"])

    for i, (x, y) in enumerate(case["positions"]):
        terminal = Terminal.Terminal(f"T{i}")
        terminal.setPlaceCoordinate(x, y)
        terminals.addTerminal(terminal)

    return die, terminals


def verify_result(result, case):
    lx, ly, hx, hy = case["die"]
    terminal_w, terminal_h = case["terminal_size"]
    spacing = case["terminal_spacing"]

    for i, (x, y) in enumerate(result):
        assert lx <= x and x + terminal_w <= hx, (i, x, y)
        assert ly <= y and y + terminal_h <= hy, (i, x, y)

    for i, (x1, y1) in enumerate(result):
        for j in range(i + 1, len(result)):
            x2, y2 = result[j]
            separated_x = (
                x1 + terminal_w + spacing <= x2
                or x2 + terminal_w + spacing <= x1
            )
            separated_y = (
                y1 + terminal_h + spacing <= y2
                or y2 + terminal_h + spacing <= y1
            )
            assert separated_x or separated_y, (i, j, result[i], result[j])


def displacement(original, result):
    moves = [
        abs(x1 - x0) + abs(y1 - y0)
        for (x0, y0), (x1, y1) in zip(original, result)
    ]
    return sum(moves), max(moves) if moves else 0


def hpwl(points):
    if not points:
        return 0
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return max(xs) - min(xs) + max(ys) - min(ys)


def total_hpwl(case, positions):
    nets = case.get("nets")
    if not nets:
        return hpwl(positions)

    total = 0
    for net in nets:
        net_points = [positions[i] for i in net]
        total += hpwl(net_points)
    return total


def is_legal_position(index, candidate, result, case):
    lx, ly, hx, hy = case["die"]
    terminal_w, terminal_h = case["terminal_size"]
    spacing = case["terminal_spacing"]
    x, y = candidate

    if x < lx or y < ly or x + terminal_w > hx or y + terminal_h > hy:
        return False

    for j, (other_x, other_y) in enumerate(result):
        if j == index:
            continue
        separated_x = (
            x + terminal_w + spacing <= other_x
            or other_x + terminal_w + spacing <= x
        )
        separated_y = (
            y + terminal_h + spacing <= other_y
            or other_y + terminal_h + spacing <= y
        )
        if not (separated_x or separated_y):
            return False
    return True


def distance_to_gp(point, gp):
    return abs(point[0] - gp[0]) + abs(point[1] - gp[1])


def total_displacement_for_result(gp_positions, result):
    return sum(
        abs(x1 - x0) + abs(y1 - y0)
        for (x0, y0), (x1, y1) in zip(gp_positions, result)
    )


def mylegal_recover(case, initial_result, passes=2, hpwl_weight=1.0):
    result = [tuple(point) for point in initial_result]
    gp_positions = [tuple(point) for point in case["positions"]]
    terminal_w, terminal_h = case["terminal_size"]
    spacing = case["terminal_spacing"]
    base_step = max(1, min(terminal_w, terminal_h, spacing) // 2)

    def toward_values(current_value, gp_value):
        delta = gp_value - current_value
        if delta == 0:
            return [current_value]

        sign = 1 if delta > 0 else -1
        values = {gp_value}
        step = base_step
        while step < abs(delta):
            values.add(current_value + sign * step)
            step *= 2
        values.add(current_value + delta // 2)
        return sorted(values, key=lambda value: abs(value - gp_value))

    for _ in range(passes):
        improved = False
        current_total_disp = total_displacement_for_result(gp_positions, result)
        current_hpwl = total_hpwl(case, result)
        order = sorted(
            range(len(result)),
            key=lambda i: distance_to_gp(result[i], gp_positions[i]),
            reverse=True,
        )
        for i in order:
            current = result[i]
            gp = gp_positions[i]
            current_dist = distance_to_gp(current, gp)
            if current_dist == 0:
                continue

            x_values = toward_values(current[0], gp[0])
            y_values = toward_values(current[1], gp[1])

            best = current
            best_dist = current_dist
            best_score = (
                current_total_disp + hpwl_weight * current_hpwl,
                current_total_disp,
                current_hpwl,
                current_dist,
            )
            candidates = []
            for x in x_values:
                candidates.append((x, current[1]))
            for y in y_values:
                candidates.append((current[0], y))
            for x in x_values[:4]:
                for y in y_values[:4]:
                    candidates.append((x, y))

            for candidate in candidates:
                if candidate == current:
                    continue
                candidate_dist = distance_to_gp(candidate, gp)
                if candidate_dist >= best_dist:
                    continue
                if not is_legal_position(i, candidate, result, case):
                    continue

                candidate_result = list(result)
                candidate_result[i] = candidate
                candidate_total_disp = current_total_disp - current_dist + candidate_dist
                candidate_hpwl = total_hpwl(case, candidate_result)
                if candidate_hpwl > current_hpwl:
                    continue
                weighted_cost = candidate_total_disp + hpwl_weight * candidate_hpwl
                candidate_score = (
                    weighted_cost,
                    candidate_total_disp,
                    candidate_hpwl,
                    candidate_dist,
                )
                if candidate_score < best_score:
                    best = candidate
                    best_dist = candidate_dist
                    best_score = candidate_score

            if best != current:
                result[i] = best
                current_total_disp = best_score[2]
                current_hpwl = best_score[3]
                improved = True
        if not improved:
            break

    return result


def run_legalization(case, mode):
    die, terminals = make_inputs(case)

    if mode == "nglic":
        legalization = Legalization()
        legalization.read({"die": die, "terminals": terminals})
        legalization.scale_by_spacing()
        legalization.legalize(expandX=1, expandY=1, initialX=1, initialY=1)
        return legalization.dplacer.result()

    if mode == "mylegal":
        nglic_result = run_legalization(case, "nglic")
        return mylegal_recover(case, nglic_result)

    if mode == "abacus":
        dplacer = dplacer_horizon.Dplacer()
        dplacer.read({
            "die": die,
            "terminals": terminals,
            "expandX": 1,
            "expandY": 1,
            "initialX": 1,
            "initialY": 1,
        })
        dplacer.buildSegments()
        dplacer.abacus(0)
        return dplacer.result()

    raise ValueError(f"unknown mode: {mode}")


def run_legalization_quiet(case, mode, verbose):
    if verbose:
        return run_legalization(case, mode)

    with contextlib.redirect_stdout(io.StringIO()):
        return run_legalization(case, mode)


def metrics(case, result):
    verify_result(result, case)
    total_disp, max_disp = displacement(case["positions"], result)
    gp_hpwl = total_hpwl(case, case["positions"])
    legal_hpwl = total_hpwl(case, result)
    return {
        "total_disp": total_disp,
        "max_disp": max_disp,
        "hpwl_growth": legal_hpwl - gp_hpwl,
    }


def improvement(base, new):
    if base == 0:
        return 0.0 if new == 0 else float("-inf")
    return (base - new) / base * 100.0


def run_case(path, compare, csv, verbose):
    case = load_case(path)
    modes = ["abacus", "nglic", "mylegal"] if compare else ["nglic"]
    rows = []
    for mode in modes:
        result = run_legalization_quiet(case, mode, verbose)
        row = metrics(case, result)
        row["mode"] = mode
        rows.append(row)

    case_name = case.get("name", path.stem)
    if csv or not compare:
        for row in rows:
            print(
                f"{case_name},{row['mode']},{len(case['positions'])},"
                f"{row['total_disp']},{row['max_disp']},{row['hpwl_growth']}"
            )
        return rows

    by_mode = {row["mode"]: row for row in rows}
    abacus = by_mode["abacus"]
    nglic = by_mode["nglic"]
    mylegal = by_mode["mylegal"]
    nglic_total_improvement = improvement(abacus["total_disp"], nglic["total_disp"])
    mylegal_total_improvement = improvement(abacus["total_disp"], mylegal["total_disp"])
    nglic_max_improvement = improvement(abacus["max_disp"], nglic["max_disp"])
    mylegal_max_improvement = improvement(abacus["max_disp"], mylegal["max_disp"])
    print(
        f"{case_name:24} {len(case['positions']):>4} "
        f"{abacus['total_disp']:>10} {nglic['total_disp']:>10} {mylegal['total_disp']:>10} "
        f"{nglic_total_improvement:>9.2f}% {mylegal_total_improvement:>9.2f}% "
        f"{abacus['max_disp']:>8} {nglic['max_disp']:>8} {mylegal['max_disp']:>8} "
        f"{nglic_max_improvement:>9.2f}% {mylegal_max_improvement:>9.2f}% "
        f"{abacus['hpwl_growth']:>10} {nglic['hpwl_growth']:>10} {mylegal['hpwl_growth']:>10}"
    )
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs="+", type=Path)
    parser.add_argument("--compare-abacus", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.csv:
        print("case,mode,n,total_disp,max_disp,hpwl_growth")
    elif args.compare_abacus:
        print(
            f"{'case':24} {'n':>4} "
            f"{'ab_total':>10} {'ng_total':>10} {'my_total':>10} "
            f"{'ng_imp':>10} {'my_imp':>10} "
            f"{'ab_max':>8} {'ng_max':>8} {'my_max':>8} "
            f"{'ng_max_imp':>10} {'my_max_imp':>10} "
            f"{'ab_hpwl':>10} {'ng_hpwl':>10} {'my_hpwl':>10}"
        )

    for case in args.cases:
        run_case(case, compare=args.compare_abacus, csv=args.csv, verbose=args.verbose)


if __name__ == "__main__":
    main()
