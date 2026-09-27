"""A runner that spawns a PEP 723 script with `sys.executable` owns that script's deps (G32, #34).

`uv run render_cover.py` ran the provider (paid) and then died in `conform_cover.py` with
`No module named 'PIL'`: the conform was spawned as `[sys.executable, conform_cover.py]`, and
under `uv run` sys.executable is an ephemeral interpreter carrying ONLY the runner's own
declared dependencies. The runner declared none. So every skill script that spawns another
with sys.executable must declare (at least) the dependencies of every script it spawns.
Checked across every skill, not just the cover, because reroll-slot had the same shape.
"""
import re
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
BLOCK = re.compile(r"^# /// script\s*\n(.*?)^# ///", re.M | re.S)


def declared(path: Path) -> set:
    m = BLOCK.search(path.read_text(encoding="utf-8", errors="replace"))
    if not m:
        return set()
    deps = re.search(r"dependencies\s*=\s*\[(.*?)\]", m.group(1), re.S)
    if not deps:
        return set()
    return {re.split(r"[<>=!~ ]", d.strip().strip("\"'"))[0].lower()
            for d in deps.group(1).replace("#", ",").split(",")
            if d.strip().strip("\"'")}


class TestTransitivePep723(unittest.TestCase):
    def test_every_sys_executable_spawner_declares_its_childrens_deps(self):
        scripts = {p.name: p for p in SKILLS.glob("*/scripts/*.py")}
        problems = []
        for p in sorted(SKILLS.glob("*/scripts/*.py")):
            src = p.read_text(encoding="utf-8", errors="replace")
            if "sys.executable" not in src:
                continue
            mine = declared(p)
            # A spawned script is named near the spawn: either inline in the same command
            # list, or as a module constant (`GENERATE = ... / "generate.py"`) that the
            # command uses by name. Collect both.
            lines = src.splitlines()
            consts = {m.group(1): m.group(2) for m in re.finditer(
                r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=.*[\"'/]([A-Za-z0-9_]+\.py)[\"']", src, re.M)}
            spawned = set()
            for i, line in enumerate(lines):
                if "sys.executable" not in line:
                    continue
                window = "\n".join(lines[i:i + 3])
                spawned |= set(re.findall(r"[\"'/]([A-Za-z0-9_]+\.py)[\"']", window))
                spawned |= {v for k, v in consts.items() if re.search(rf"\b{k}\b", window)}
            for name in sorted(spawned):
                child = scripts.get(name)
                if child is None or child == p:
                    continue
                need = declared(child) - mine
                if need:
                    problems.append(f"{p.relative_to(SKILLS)} spawns {name}, which needs "
                                    f"{sorted(need)}; declare them in its own # /// script block")
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
