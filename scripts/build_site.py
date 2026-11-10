"""Build the presentation with local media."""
from pathlib import Path
import shutil
import subprocess
root = Path(__file__).resolve().parents[1]
out = root / "_site"
if out.exists():
    shutil.rmtree(out)
subprocess.run(["quarto", "render", "index.qmd"], cwd=root, check=True)
print(f"Preview: {out / 'index.html'}")
