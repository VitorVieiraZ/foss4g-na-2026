"""Test a generated build script in QGIS without opening a window.

Usage (with QGIS's own Python; see SKILL.md "Testing"):
    python3 run_in_qgis.py build_<name>.py --parent /tmp/mm-test

Builds the project inside --parent (instead of the user's folder), then runs
templates/check_project.py on it. Exit code 1 if anything must be fixed.
"""
import argparse
import os
import re
import sys
import tempfile

from qgis.core import QgsApplication, QgsProject

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "..", "templates", "check_project.py")

args = argparse.ArgumentParser()
args.add_argument("script")
args.add_argument("--parent", required=True)
opts = args.parse_args()

# Tests only ever build inside a temporary folder, never in real project folders.
temp_roots = {os.path.realpath(tempfile.gettempdir()), os.path.realpath("/tmp"), os.path.realpath("/private/tmp")}
parent = os.path.realpath(opts.parent)
if not any(parent == r or parent.startswith(r + os.sep) for r in temp_roots):
    sys.exit(f"run_in_qgis.py: --parent must be inside a temporary folder ({tempfile.gettempdir()})")
if re.search(r'(?m)^MODE = "add"', open(opts.script).read()):
    sys.exit("run_in_qgis.py: tests 'new' mode only. For 'add', test on a copy (see SKILL.md).")

prefix = os.environ.get("QGIS_PREFIX_PATH", "/Applications/QGIS.app/Contents/MacOS")
QgsApplication.setPrefixPath(prefix, True)
app = QgsApplication([], False)
app.initQgis()

source = open(opts.script).read()
source = re.sub(r"(?m)^PARENT_FOLDER = .*$", f"PARENT_FOLDER = {opts.parent!r}", source)
os.makedirs(opts.parent, exist_ok=True)
exec(compile(source, opts.script, "exec"), {"__name__": "__main__"})

saved = QgsProject.instance().fileName()
QgsProject.instance().clear()
QgsProject.instance().read(saved)
scope = {"__name__": "__main__"}
exec(compile(open(CHECKER).read(), CHECKER, "exec"), scope)
app.exitQgis()
sys.exit(1 if scope["problems"] else 0)
