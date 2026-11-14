"""Put a built setup into updates/ so installed copies of ClipDrop find it.

Usage:  python tools/publish_update.py ClipDrop-Setup-5.1.exe notes.md
notes.md: English notes, then a line "<!-- ar -->", then Arabic notes.
Then commit and push updates/ to the main branch.
"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
exe, notes = Path(sys.argv[1]), Path(sys.argv[2]).read_text(encoding="utf-8")
version = re.search(r"(\d+(?:\.\d+)+)", exe.name).group(1)
en, _, ar = notes.partition("<!-- ar -->")
en = en.replace("<!-- en -->", "").strip()
ar = ar.strip()
out = root / "updates"
out.mkdir(exist_ok=True)
for old in out.glob("ClipDrop-Setup-*.exe"):   # keep only the newest numbered setup in the folder
    old.unlink()
shutil.copyfile(exe, out / exe.name)
shutil.copyfile(exe, out / "ClipDrop-Setup.exe")   # always the newest: the download link on the GitHub page
data = exe.read_bytes()
(out / "latest.json").write_text(json.dumps({
    "version": version, "file": exe.name, "size": len(data),
    "sha256": hashlib.sha256(data).hexdigest(), "notes_en": en, "notes_ar": ar,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
changes = out / "CHANGES.md"
old = changes.read_text(encoding="utf-8") if changes.exists() else "# ClipDrop versions\n"
head, _, rest = old.partition("\n")
entry = f"\n## {version}\n\n{en}\n\n<div dir=\"rtl\">\n\n{ar}\n\n</div>\n"
changes.write_text(head + "\n" + entry + rest, encoding="utf-8")
print(f"updates/ now offers {version} ({len(data)} bytes)")
