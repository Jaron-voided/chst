"""Check that TODO.md assigns every acceptance ID to exactly one task.

Run from the repository root as `python3.14 -I tools/todo_coverage.py`. Standard library only.
Exits 0 when TODO.md is consistent with ACCEPTANCE.md, 1 otherwise, printing each problem.

A task is a top-level `- [ ] **<ID>` line in TODO.md, up to the next task, heading, `---` or
`**STOP` line. Inside a task, the IDs on its `Checks` bullet (and that bullet's indented
continuation lines) are the IDs it owns; the IDs on its `Re-check` bullet are ones it only
re-runs. It fails when:
- an ACCEPTANCE.md ID is owned by no task, or by more than one;
- TODO.md names an ID that isn't in ACCEPTANCE.md;
- a task's Re-check bullet lists an ID that the same task lists under Checks;
- a task mentions an ID that is on neither its Checks nor its Re-check bullet;
- a Checks or Re-check bullet uses a range (`AC-X-1 … AC-X-4`) instead of listing each ID.
"""

import argparse
import re
import sys
from collections import defaultdict

ID = re.compile(r'AC-[A-Z]+(?:-[A-Z]+)?-\d+W?\b')
TASK = re.compile(r'- \[[ x]\] \*\*([A-Z]+-\d+[a-z]?)')
BULLET = re.compile(r'  - (Checks|Re-check)\b')


def acceptance_ids(path):
    with open(path, encoding='utf-8') as f:
        return re.findall(r'^#### (AC-[A-Z0-9-]+) ', f.read(), re.M)


def tasks(lines):
    """Yield (task_id, block_lines), the block starting with the task's own line."""
    cur = None
    for line in lines:
        m = TASK.match(line)
        if m:
            if cur:
                yield cur
            cur = (m.group(1), [line])
        elif re.match(r'(#|---|\*\*STOP)', line):
            if cur:
                yield cur
            cur = None
        elif cur:
            cur[1].append(line)
    if cur:
        yield cur


def check(acc_path, todo_path):
    acc = acceptance_ids(acc_path)
    with open(todo_path, encoding='utf-8') as f:
        todo = f.read().splitlines()
    errors, owners = [], defaultdict(list)
    for tid, block in tasks(todo):
        owned, rechecked, kind = set(), set(), None
        for line in block[1:]:
            m = BULLET.match(line)
            if m:
                kind = m.group(1)
            elif not line.startswith('    '):
                kind = None          # a new bullet at task level, or the end of the block
            if kind and '…' in line and ID.search(line):
                errors.append(f'{tid}: range on its {kind} line: {line.strip()}')
            if kind == 'Checks':
                owned |= set(ID.findall(line))
            elif kind == 'Re-check':
                rechecked |= set(ID.findall(line))
        for i in owned:
            owners[i].append(tid)
        both = owned & rechecked
        if both:
            errors.append(f'{tid}: Re-check lists IDs it also has under Checks: {sorted(both)}')
        loose = set(ID.findall('\n'.join(block))) - owned - rechecked
        if loose:
            errors.append(f'{tid}: mentions IDs on neither Checks nor Re-check: {sorted(loose)}')
    for i in acc:
        if len(owners[i]) != 1:
            errors.append(f'{i}: owned by {", ".join(owners[i]) if owners[i] else "no task"}')
    unknown = sorted(set(ID.findall('\n'.join(todo))) - set(acc))
    if unknown:
        errors.append(f'unknown IDs (not in {acc_path}): {unknown}')
    once = sum(len(owners[i]) == 1 for i in acc)
    print(f'acceptance IDs: {len(acc)}; owned by exactly one task: {once}')
    for e in errors:
        print(f'ERROR {e}')
    return not errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--acceptance', default='ACCEPTANCE.md')
    ap.add_argument('--todo', default='TODO.md')
    a = ap.parse_args()
    sys.exit(0 if check(a.acceptance, a.todo) else 1)


if __name__ == '__main__':
    main()
