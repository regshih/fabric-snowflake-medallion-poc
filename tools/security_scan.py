#!/usr/bin/env python3
"""Fail closed when likely credentials are present in files or Git history."""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess  # nosec B404 - scanner invokes git with argument arrays and shell disabled
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
DOCUMENTED_EXAMPLE = (ROOT / "SECURITY.md").resolve()
GIT_EXE = shutil.which("git")
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".pyc"}
PATTERNS = {
    "azure-storage-key": re.compile(r"AccountKey=[A-Za-z0-9+/]{32,}={0,2}", re.IGNORECASE),
    "sas-signature": re.compile(r"(?:[?&;]|^)sig=[A-Za-z0-9%+/]{20,}", re.IGNORECASE),
    "github-token": re.compile(r"(?:\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b)"),
    "databricks-token": re.compile(r"\bdapi[a-f0-9]{20,}\b", re.IGNORECASE),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\b"),
    "private-key": re.compile(r"-----BEGIN (?:ENCRYPTED |RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "literal-secret": re.compile(
        r"(?:client[_-]?secret|password|pwd|access[_-]?token)\s*[:=]\s*[\"'][^<$%{][^\"'\r\n]{7,}[\"']",
        re.IGNORECASE,
    ),
    "literal-bearer": re.compile(r"Authorization\s*[:=]\s*[\"']Bearer\s+[A-Za-z0-9._~+/-]{16,}", re.IGNORECASE),
    "live-environment-guid": re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
        re.IGNORECASE,
    ),
    "snowflake-snowsight-account-url": re.compile(
        r"https://app\.snowflake\.com/[a-z0-9_-]+/[a-z0-9_-]+(?:/|\b)", re.IGNORECASE
    ),
    "snowflake-account-host": re.compile(
        r"\b[a-z0-9_-]+(?:\.[a-z0-9_-]+)*\.(?:privatelink\.)?snowflakecomputing\.(?:com|cn)\b",
        re.IGNORECASE,
    ),
}
SAFE_TEST_LITERALS = {
    "github_pat_synthetic_test_value",
    "Org-Account.snowflakecomputing.com",
    "Org-Account.privatelink.snowflakecomputing.com",
    "org-account.snowflakecomputing.com",
    "org-account.privatelink.snowflakecomputing.com",
    "acme-demo.snowflakecomputing.com",
}


def git(*args: str) -> str:
    if not GIT_EXE:
        raise RuntimeError("git executable was not found on PATH")
    result = subprocess.run(  # nosec B603 - fixed executable and argument list; no shell
        [GIT_EXE, "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def scan_text(label: str, text: str) -> list[str]:
    findings: list[str] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        candidate = line
        for safe_literal in SAFE_TEST_LITERALS:
            candidate = candidate.replace(safe_literal, "<known-test-fixture>")
        for name, pattern in PATTERNS.items():
            if pattern.search(candidate):
                findings.append(f"{label}:{line_number}: {name}")
    return findings


def working_tree_files() -> list[Path]:
    names = git("ls-files", "--cached", "--others", "--exclude-standard", "-z").split("\0")
    return [ROOT / name for name in names if name]


def scan_working_tree() -> list[str]:
    findings: list[str] = []
    for path in working_tree_files():
        if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if path.resolve() in {SELF, DOCUMENTED_EXAMPLE}:
            continue
        try:
            findings.extend(scan_text(path.relative_to(ROOT).as_posix(), path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue
    return findings


def scan_history() -> list[str]:
    if not GIT_EXE:
        raise RuntimeError("git executable was not found on PATH")
    commits = [value for value in git("rev-list", "--all").splitlines() if value]
    findings: list[str] = []
    for commit in commits:
        for name in git("ls-tree", "-r", "--name-only", commit).splitlines():
            path = ROOT / name
            if path.suffix.lower() in SKIP_SUFFIXES or name in {"tools/security_scan.py", "SECURITY.md"}:
                continue
            result = subprocess.run(  # nosec B603 - fixed executable and argument list; no shell
                [GIT_EXE, "-C", str(ROOT), "show", f"{commit}:{name}"],
                capture_output=True,
                check=False,
            )
            if result.returncode or b"\0" in result.stdout[:8192]:
                continue
            text = result.stdout.decode("utf-8", errors="replace")
            findings.extend(scan_text(f"{commit[:12]}:{name}", text))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--working-tree", action="store_true")
    parser.add_argument("--git-history", action="store_true")
    args = parser.parse_args()
    if not args.working_tree and not args.git_history:
        parser.error("select --working-tree and/or --git-history")

    findings: list[str] = []
    if args.working_tree:
        findings.extend(scan_working_tree())
    if args.git_history:
        findings.extend(scan_history())
    if findings:
        print("SECURITY SCAN FAILED")
        print("\n".join(sorted(set(findings))))
        return 1
    print("SECURITY SCAN PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
