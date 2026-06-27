import random

import Die
import Terminal
from Legalization import Legalization


def main():
    random.seed(7)

    die = Die.Die()
    die.setDieSize(0, 0, 1000, 1000)

    terminals = Terminal.Terminals()
    terminal_size = 6
    terminal_spacing = 11
    terminals.setTerminalSize(terminal_size, terminal_size)
    terminals.setTerminalSpacing(terminal_spacing)

    original_positions = [
        [random.randint(10, 300), random.randint(10, 300)]
        for _ in range(100)
    ]
    for i, (x, y) in enumerate(original_positions):
        terminal = Terminal.Terminal(i)
        terminal.setPlaceCoordinate(x, y)
        terminals.addTerminal(terminal)

    legalization = Legalization()
    legalization.read({"die": die, "terminals": terminals})
    legalization.scale_by_spacing()
    legalization.legalize(expandX=1, expandY=1, initialX=1, initialY=1)

    result = legalization.dplacer.result()
    assert len(result) == len(original_positions)

    for i, (x, y) in enumerate(result):
        assert 0 <= x and x + terminal_size <= 1000, (i, x, y)
        assert 0 <= y and y + terminal_size <= 1000, (i, x, y)

    for i, (x1, y1) in enumerate(result):
        for j in range(i + 1, len(result)):
            x2, y2 = result[j]
            separated_x = (
                x1 + terminal_size + terminal_spacing <= x2
                or x2 + terminal_size + terminal_spacing <= x1
            )
            separated_y = (
                y1 + terminal_size + terminal_spacing <= y2
                or y2 + terminal_size + terminal_spacing <= y1
            )
            assert separated_x or separated_y, (i, j, result[i], result[j])

    print(f"verified {len(result)} placements")


if __name__ == "__main__":
    main()
