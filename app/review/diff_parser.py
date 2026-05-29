def build_position_mapping(patch: str, new_start: int) -> dict[int, int]:
    mapping: dict[int, int] = {}
    current_line = new_start
    position = 0

    for raw_line in patch.splitlines():
        if raw_line.startswith("@@"):
            continue
        position += 1
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            mapping[current_line] = position
            current_line += 1
            continue
        if raw_line.startswith("-") and not raw_line.startswith("---"):
            continue
        current_line += 1

    return mapping
