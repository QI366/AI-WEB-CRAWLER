"""生成项目结构树，可打印到终端或写入 Markdown 文件。

用法:
    python scripts/project_tree.py
    python scripts/project_tree.py --max-depth 2 --dirs-only
    python scripts/project_tree.py -o STRUCTURE.md
"""

import argparse
import fnmatch
import os
import sys
from pathlib import Path

DEFAULT_IGNORES = (
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "node_modules",
    "*.egg-info",
    "*.pyc",
    ".DS_Store",
)

GLYPHS = {
    "unicode": {"branch": "├── ", "last": "└── ", "pipe": "│   ", "blank": "    "},
    "ascii": {"branch": "|-- ", "last": "`-- ", "pipe": "|   ", "blank": "    "},
}


def is_ignored(name: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"


def list_entries(directory: Path, patterns: tuple[str, ...], dirs_only: bool) -> list[Path]:
    try:
        entries = list(directory.iterdir())
    except PermissionError:
        return []
    entries = [e for e in entries if not is_ignored(e.name, patterns)]
    if dirs_only:
        entries = [e for e in entries if e.is_dir()]
    return sorted(entries, key=lambda e: (e.is_file(), e.name.lower()))


def build_tree(
    directory: Path,
    patterns: tuple[str, ...],
    max_depth: int,
    dirs_only: bool,
    show_size: bool,
    glyphs: dict[str, str],
    prefix: str = "",
    depth: int = 1,
) -> tuple[list[str], int, int]:
    lines: list[str] = []
    dir_count = 0
    file_count = 0

    entries = list_entries(directory, patterns, dirs_only)
    for index, entry in enumerate(entries):
        is_last = index == len(entries) - 1
        connector = glyphs["last"] if is_last else glyphs["branch"]

        if entry.is_dir():
            dir_count += 1
            lines.append(f"{prefix}{connector}{entry.name}/")
            if max_depth and depth >= max_depth:
                continue
            child_prefix = prefix + (glyphs["blank"] if is_last else glyphs["pipe"])
            child_lines, child_dirs, child_files = build_tree(
                entry,
                patterns,
                max_depth,
                dirs_only,
                show_size,
                glyphs,
                child_prefix,
                depth + 1,
            )
            lines.extend(child_lines)
            dir_count += child_dirs
            file_count += child_files
        else:
            file_count += 1
            suffix = f"  ({human_size(entry.stat().st_size)})" if show_size else ""
            lines.append(f"{prefix}{connector}{entry.name}{suffix}")

    return lines, dir_count, file_count


def render(root: Path, args: argparse.Namespace) -> str:
    patterns = () if args.all else DEFAULT_IGNORES + tuple(args.ignore)
    glyphs = GLYPHS["ascii" if args.ascii else "unicode"]

    lines, dir_count, file_count = build_tree(
        root,
        patterns,
        args.max_depth,
        args.dirs_only,
        args.size,
        glyphs,
    )

    body = "\n".join([f"{root.name}/", *lines])
    summary = f"\n{dir_count} 个目录, {file_count} 个文件"
    return body + summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成项目结构树")
    parser.add_argument(
        "root",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent),
        help="项目根目录（默认为脚本所在项目的根目录）",
    )
    parser.add_argument("-d", "--max-depth", type=int, default=0, help="最大层级，0 表示不限制")
    parser.add_argument("-o", "--output", help="写入文件，例如 STRUCTURE.md")
    parser.add_argument("-a", "--all", action="store_true", help="不忽略任何文件")
    parser.add_argument("--dirs-only", action="store_true", help="只显示目录")
    parser.add_argument("--size", action="store_true", help="显示文件大小")
    parser.add_argument("--ascii", action="store_true", help="使用 ASCII 字符绘制")
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="PATTERN",
        help="额外的忽略规则，可重复传入，支持通配符",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"目录不存在: {root}", file=sys.stderr)
        return 1

    tree = render(root, args)

    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = root / output_path
        content = f"# 项目结构\n\n```\n{tree}\n```\n"
        output_path.write_text(content, encoding="utf-8")
        print(f"已写入 {output_path}")
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(tree)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
