#!/usr/bin/env python3
"""First-run guide for the Savage Sales Agent. Works on Windows, macOS and Linux. Standard library only.

  python setup.py            check your machine, prepare the folder, then open the agent in setup mode
  python setup.py --check    only run the checks (no launching)
  python setup.py --launch   normal start: guided setup the first time, straight to the agent after that
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MARKER = os.path.join(HERE, ".savage_setup_done")


def say(msg=""):
    print(msg, flush=True)


def check_environment():
    """Return (ok, problems). Prints a friendly checklist."""
    problems = []
    say("Checking your computer...\n")

    if sys.version_info >= (3, 9):
        say(f"  [ok] Python {sys.version_info.major}.{sys.version_info.minor}")
    else:
        say(f"  [!!] Python {sys.version_info.major}.{sys.version_info.minor} is too old (need 3.9+)")
        problems.append("Install Python 3.9 or newer from https://www.python.org/downloads/")

    claude = shutil.which("claude")
    if claude:
        say("  [ok] Claude Code is installed")
    else:
        say("  [!!] Claude Code is not installed")
        problems.append("Install Claude Code (the engine this tool runs on): https://docs.claude.com/en/docs/claude-code/setup\n"
                        "       then run `claude` once and sign in with your Claude account.")

    if shutil.which("git"):
        say("  [ok] git (optional, for updates)")
    else:
        say("  [--] git not found (optional; you can still use the tool)")

    for d in ("outputs", "deals"):
        os.makedirs(os.path.join(HERE, d), exist_ok=True)
    profile = os.path.join(HERE, "profile.md")
    template = os.path.join(HERE, "profile.template.md")
    if not os.path.exists(profile) and os.path.exists(template):
        shutil.copyfile(template, profile)
        say("  [ok] created your blank profile.md")
    else:
        say("  [ok] profile.md present")

    # Self-test: make sure the bundled tests pass on this machine.
    try:
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                           cwd=HERE, capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            say("  [ok] self-test passed")
        else:
            say("  [!!] self-test failed (the tool may still work, but tell the maintainers)")
            say("       " + (r.stderr.strip().splitlines() or ["unknown error"])[-1])
    except (OSError, subprocess.SubprocessError) as e:
        say(f"  [--] could not run self-test: {e}")

    return not problems, problems


def launch(first_run):
    claude = shutil.which("claude")
    if not claude:
        return 1
    os.chdir(HERE)
    if first_run:
        say("\nOpening the agent. It will ask a few questions to set you up.")
        say("(Not selling anything yet? Choose practice mode when asked.)\n")
        args = [claude, "/setup"]
    else:
        args = [claude]
    # On Windows claude is a .cmd/.exe shim; subprocess handles it. Wait so the terminal stays attached.
    code = subprocess.call(args, cwd=HERE)
    if first_run and code == 0:
        open(MARKER, "w").write("setup started\n")
    return code


def main(argv):
    check_only = "--check" in argv
    launch_mode = "--launch" in argv
    first_run = not os.path.exists(MARKER)

    if launch_mode and not first_run:
        return launch(first_run=False)

    say("=" * 60)
    say(" Savage Sales Agent: first-time setup" if first_run else " Savage Sales Agent: checks")
    say("=" * 60 + "\n")
    ok, problems = check_environment()
    if not ok:
        say("\nA few things need fixing first:\n")
        for i, p in enumerate(problems, 1):
            say(f" {i}. {p}")
        say("\nWhen done, run this again: python setup.py")
        return 1
    say("\nEverything looks good.")
    if check_only:
        return 0
    return launch(first_run=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
