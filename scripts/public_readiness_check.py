from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_TEXT_SUFFIXES = {'.md', '.py', '.toml', '.yaml', '.yml', '.json', '.txt'}
DENY_PATH_PARTS = {'.git', '.pytest_cache', '.ruff_cache', '__pycache__', 'dist', 'build'}
LOCAL_PATH_RE = re.compile(r'/Users/[A-Za-z0-9_.-]+')
SECRET_PATTERNS = [
    re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----'),
    re.compile(r'(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*["\']?[A-Za-z0-9_./+=-]{20,}'),
    re.compile(r'gh[opsu]_[A-Za-z0-9_]{20,}'),
]
FORBIDDEN_NAMES = {
    'state.db',
    'MEMORY.md',
    'USER.md',
    'latest-brief.md',
}
ALLOW_LOCAL_PATHS = {
    Path('docs/plans/2026-05-05-public-facing-prep.md'),
}
REQUIRED_README = ['Quickstart', 'Architecture', 'Safety', 'Configuration', 'Hermes adapter', 'Development', 'License']
REQUIRED_DOCS = [
    'docs/architecture.md',
    'docs/safety.md',
    'docs/cli.md',
    'docs/configuration.md',
    'docs/hermes-adapter.md',
    'docs/release-readiness.md',
    'docs/skills.md',
    'docs/testing-quickstart.md',
    'docs/remediation-plans.md',
    'docs/scheduling-and-notifications.md',
    'docs/history/README.md',
    'adapters/hermes/skills/eva/SKILL.md',
    'LICENSE',
    'CHANGELOG.md',
    'CONTRIBUTING.md',
    'SECURITY.md',
    '.github/workflows/ci.yml',
]


def fail(message: str) -> None:
    print(f'FAIL {message}', file=sys.stderr)
    raise SystemExit(1)


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    paths = [Path(line) for line in result.stdout.splitlines() if line.strip()]
    return [path for path in paths if (ROOT / path).exists()]


def text_for(path: Path) -> str | None:
    if path.suffix not in PUBLIC_TEXT_SUFFIXES:
        return None
    try:
        return (ROOT / path).read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return None


def check_required_files(files: set[Path]) -> None:
    missing = [p for p in REQUIRED_DOCS if Path(p) not in files]
    if missing:
        fail(f'missing required files: {missing}')


def check_readme() -> None:
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    missing = [s for s in REQUIRED_README if s.lower() not in text.lower()]
    if missing:
        fail(f'README missing sections: {missing}')


def check_private_artifacts(files: list[Path]) -> None:
    for path in files:
        if any(part in DENY_PATH_PARTS for part in path.parts):
            continue
        if path.name in FORBIDDEN_NAMES:
            fail(f'forbidden runtime artifact tracked: {path}')
        if 'eva-vault' in path.parts:
            fail(f'generated vault path tracked: {path}')
        if path.suffix in {'.db', '.sqlite', '.sqlite3', '.jsonl'}:
            fail(f'possible live/generated artifact tracked: {path}')


def check_text_patterns(files: list[Path]) -> None:
    for path in files:
        text = text_for(path)
        if text is None:
            continue
        if path not in ALLOW_LOCAL_PATHS and LOCAL_PATH_RE.search(text):
            fail(f'local absolute path found in {path}')
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                fail(f'possible secret pattern found in {path}')
        if path.as_posix().startswith('adapters/hermes/') or path.as_posix().startswith('docs/') or path == Path('README.md'):
            for phrase in ['home channel', 'Telegram home channel']:
                if phrase.lower() in text.lower():
                    fail(f'private delivery phrase found in {path}: {phrase}')


def check_no_write_smoke() -> None:
    env = os.environ.copy()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        profiles = tmp_path / 'profiles'
        vault = tmp_path / 'vault'
        profiles.mkdir()
        cmd = [sys.executable, '-m', 'eva.loop', '--profiles-dir', str(profiles), '--vault', str(vault), '--no-write', '--json']
        result = subprocess.run(cmd, cwd=ROOT, env={**env, 'PYTHONPATH': str(ROOT / 'src')}, text=True, capture_output=True)
        if result.returncode != 0:
            fail(f'no-write smoke failed: {result.stderr.strip()}')
        try:
            json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            fail(f'no-write smoke did not emit JSON: {exc}')
        if vault.exists():
            fail('--no-write smoke created a vault')


def run_required_commands() -> None:
    commands = [
        [sys.executable, '-m', 'ruff', 'check', '.'],
        [sys.executable, '-m', 'pytest', '-q'],
        [sys.executable, '-m', 'compileall', '-q', 'src', 'tests'],
    ]
    for cmd in commands:
        if shutil.which(cmd[2] if cmd[1] == '-m' else cmd[0]) is None and cmd[1] != '-m':
            fail(f'missing command: {cmd}')
        result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        if result.returncode != 0:
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)
            fail(f'command failed: {" ".join(cmd)}')


def check_build_if_available() -> None:
    result = subprocess.run([sys.executable, '-m', 'build', '--version'], cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        print('SKIP package build check: build module not installed; install dev extras with: python -m pip install -e ".[dev]"')
        return
    subprocess.run([sys.executable, '-m', 'build'], cwd=ROOT, text=True, check=True)
    twine = subprocess.run([sys.executable, '-m', 'twine', '--version'], cwd=ROOT, text=True, capture_output=True)
    if twine.returncode == 0:
        dist_files = sorted(str(path) for path in (ROOT / 'dist').glob('*'))
        if not dist_files:
            fail('package build produced no dist artifacts')
        subprocess.run([sys.executable, '-m', 'twine', 'check', *dist_files], cwd=ROOT, text=True, check=True)
    else:
        print('SKIP twine check: twine module not installed; install dev extras with: python -m pip install -e ".[dev]"')


def main() -> None:
    files = tracked_files()
    file_set = set(files)
    check_required_files(file_set)
    check_readme()
    check_private_artifacts(files)
    check_text_patterns(files)
    check_no_write_smoke()
    run_required_commands()
    check_build_if_available()
    print('PASS public readiness local checks')


if __name__ == '__main__':
    main()
