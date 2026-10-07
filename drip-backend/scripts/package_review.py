"""Package an explicit source allowlist; never include local credentials or Git state."""

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
TREES = ("app", "alembic", "tests", "scripts", "docs")
FILES = (
    ".env.example",
    ".gitignore",
    ".dockerignore",
    "main.py",
    "alembic.ini",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "Dockerfile",
    "Dockerfile.worker",
    "docker-compose.yml",
    "compose.test.yml",
    "README.md",
    "PROGRESS.md",
    "SETUP.md",
    "KNOWN_LIMITS.md",
    "UPDATE_NOTES.md",
    "fix_migration.py",
    "seed_users.py",
)


def selected_files() -> list[Path]:
    paths = [ROOT / name for name in FILES if (ROOT / name).is_file()]
    for name in TREES:
        for path in (ROOT / name).rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT)
            if path.is_symlink() or any(part.startswith(".") for part in relative.parts):
                continue
            if "__pycache__" in relative.parts or path.suffix not in {
                ".py",
                ".mako",
                ".md",
                ".json",
                ".xml",
                ".txt",
            }:
                continue
            if not path.resolve().is_relative_to(ROOT):
                raise RuntimeError(f"Path escapes source tree: {relative}")
            paths.append(path)
    return sorted(set(paths))


def main() -> None:
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    destination = output / "WearHowZ_Task_6_Review.zip"
    manifest = {
        "status": "review-only; not production approved",
        "files": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in selected_files()
        },
    }
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for name in manifest["files"]:
            archive.write(ROOT / name, name)
        archive.writestr("MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    with ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP integrity check failed")
        for name, expected in manifest["files"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise RuntimeError(f"ZIP content mismatch: {name}")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    (output / "WearHowZ_Task_6_Review.sha256").write_text(
        f"{digest}  {destination.name}\n", encoding="ascii"
    )
    print(f"Verified {len(manifest['files'])} source files: {destination.name}; SHA-256 {digest}")


if __name__ == "__main__":
    main()
