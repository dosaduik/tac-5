#!/usr/bin/env -S uv run
# /// script
# dependencies = ["python-dotenv", "pydantic"]
# ///

"""
ADW Plan, Build & Test - AI Developer Workflow for agentic planning, building and testing

Usage: uv run adw_plan_build_test.py <issue-number> [adw-id]

This script runs the complete ADW pipeline:
1. adw_plan.py - Planning phase
2. adw_build.py - Implementation phase
3. adw_test.py - Testing phase

The scripts are chained together via persistent state (adw_state.json).
"""

import subprocess
import sys
import os

# Add the parent directory to Python path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adw_modules.workflow_ops import ensure_adw_id
from adw_modules.utils import configure_utf8_io


def main():
    """Main entry point."""
    # Make stdout/stderr and child processes UTF-8 safe (Windows)
    configure_utf8_io()

    if len(sys.argv) < 2:
        print("Usage: uv run adw_plan_build_test.py <issue-number> [adw-id]")
        sys.exit(1)

    issue_number = sys.argv[1]
    adw_id = sys.argv[2] if len(sys.argv) > 2 else None

    # Ensure ADW ID exists with initialized state
    adw_id = ensure_adw_id(issue_number, adw_id)
    print(f"Using ADW ID: {adw_id}")

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Run plan with the ADW ID
    plan_cmd = [
        "uv",
        "run",
        os.path.join(script_dir, "adw_plan.py"),
        issue_number,
        adw_id,
    ]
    print(f"Running: {' '.join(plan_cmd)}")
    plan = subprocess.run(plan_cmd)
    if plan.returncode != 0:
        sys.exit(1)

    # Run build with the ADW ID
    build_cmd = [
        "uv",
        "run",
        os.path.join(script_dir, "adw_build.py"),
        issue_number,
        adw_id,
    ]
    print(f"Running: {' '.join(build_cmd)}")
    build = subprocess.run(build_cmd)
    if build.returncode != 0:
        sys.exit(1)

    # Run test with the ADW ID
    test_cmd = [
        "uv",
        "run",
        os.path.join(script_dir, "adw_test.py"),
        issue_number,
        adw_id,
    ]
    print(f"Running: {' '.join(test_cmd)}")
    test = subprocess.run(test_cmd)
    if test.returncode != 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
