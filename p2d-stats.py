#!/usr/bin/env python3
"""
Aggregate total lines changed per author across multiple GitHub repos,
using git-quick-stats for the detailed stats output.
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# List of repos to aggregate over
REPOS = [
    "git@github.com:turnitin/tii-assisted-grading-services.git",
    "git@github.com:turnitin/tii-checklist-editor-services.git",
    "git@github.com:turnitin/paper-to-digital-services.git",
    "git@github.com:turnitin/tii-mfe-lib.git",
    "git@github.com:turnitin/tii-assisted-grading-mfe.git",
    "git@github.com:turnitin/region-board.git",
    "git@github.com:turnitin/tii-router.git",
    "git@github.com:turnitin/paper-to-digital-mfe.git",
]

def ensure_git_quick_stats_installed():
    try:
        subprocess.run(["git-quick-stats", "-h"], check=True, stdout=subprocess.DEVNULL)
    except Exception:
        sys.exit("Error: git-quick-stats must be installed and on your PATH")

def clone_or_update(repo_url: str, base_dir: Path) -> Path:
    name = repo_url.rstrip("/").split("/")[-1]
    dest = base_dir / name
    if dest.exists():
        print(f"[INFO] Fetching updates in {name}...")
        subprocess.run(["git", "-C", str(dest), "fetch"], check=True)
    else:
        print(f"[INFO] Cloning {name}...")
        subprocess.run(["git", "clone", repo_url, str(dest)], check=True)
    return dest

def parse_detailed_stats(output: str) -> dict:
    """
    Given the stdout of `git-quick-stats -T`, extract the
    'Contribution stats By Author' blocks and return a dict
    of { author_name: lines_changed }.
    """
    lines = output.splitlines()
    stats = {}
    # Find the Contribution stats section
    start = None
    for i, line in enumerate(lines):
        if "Contribution stats By Author" in line:
            start = i + 1
            break
    if start is None:
        return stats

    i = start
    while i < len(lines):
        header = lines[i].strip()
        # Detect author block header: Name <email>:
        m = re.match(r"^(.+?) <.+?>:$", header)
        if not m:
            i += 1
            continue
        name = m.group(1).strip()
        i += 1
        # Read indented lines in this block
        lines_changed = 0
        while i < len(lines) and lines[i].startswith(" "):
            entry = lines[i].strip()
            m2 = re.match(r"^lines changed:\s+(\d+)", entry)
            if m2:
                lines_changed = int(m2.group(1))
            i += 1
        stats[name] = stats.get(name, 0) + lines_changed
    return stats

def gather_stats(repos):
    total_per_user = {}
    grand_total = 0

    with tempfile.TemporaryDirectory() as td:
        base_dir = Path(td)
        for repo_url in repos:
            repo_path = clone_or_update(repo_url, base_dir)
            # Run git-quick-stats detailed stats
            print(f"[INFO] Generating stats in {repo_path.name}...")
            proc = subprocess.run(
                ["git-quick-stats", "-T"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=True
            )
            repo_stats = parse_detailed_stats(proc.stdout)
            for user, count in repo_stats.items():
                total_per_user[user] = total_per_user.get(user, 0) + count
                grand_total += count

    return total_per_user, grand_total

def main():
    totals, grand = gather_stats(REPOS)

    print("\n====== Total Lines Changed per User ======")
    for user, count in sorted(totals.items(), key=lambda kv: kv[1], reverse=True):
        print(f"{user}: {count} lines changed")
    print("==========================================")
    print(f"Grand total across all repos: {grand} lines changed")

if __name__ == "__main__":
    main()

