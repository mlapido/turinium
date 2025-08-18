import os
from pathlib import Path

MODULE = "turinium"
DOCS_DIR = Path("docs/reference")
SRC_DIR = Path(MODULE)

def write_autodoc_stub(module_path: Path):
    rel_module = module_path.with_suffix("").as_posix().replace("/", ".")
    out_file = DOCS_DIR / f"{rel_module.split('.')[-1]}.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    content = f"# `{rel_module}`\n\n::: {rel_module}\n"
    out_file.write_text(content)
    print(f"Generated: {out_file}")

def generate():
    if DOCS_DIR.exists():
        for f in DOCS_DIR.glob("*.md"):
            f.unlink()

    (DOCS_DIR / "index.md").write_text("# API Reference\n\n")

    for py_file in SRC_DIR.rglob("*.py"):
        if "__" in py_file.name:
            continue
        write_autodoc_stub(py_file)

if __name__ == "__main__":
    generate()
