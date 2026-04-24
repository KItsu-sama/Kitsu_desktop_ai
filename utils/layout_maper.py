""" # utils/layout_maper.py
Filesystem Snapshot Tool

- Scans a directory recursively
- Respects .gitignore rules
- Builds a tree structure
- Prints a tree layout to console
- Saves layout as text and JSON
"""

import os
import json
import fnmatch
import argparse
from pathlib import Path
from typing import List, Optional


# =========================
# Node Model
# =========================

class Node:
    def __init__(self, name: str, path: str, is_dir: bool):
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.children: List["Node"] = []

        # metadata
        self.type = "directory" if is_dir else "file"
        self.size = self._get_size()

    def _get_size(self) -> Optional[int]:
        if not self.is_dir:
            try:
                return os.path.getsize(self.path)
            except OSError:
                return None
        return None


# =========================
# .gitignore handling
# =========================

def load_gitignore(root_path: str) -> List[str]:
    patterns: List[str] = []

    ignore_file = os.path.join(root_path, ".gitignore")
    if os.path.exists(ignore_file):
        with open(ignore_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                patterns.append(line.rstrip("/"))

    # Always ignore git internals
    patterns.append(".git")
    return patterns


def is_ignored(path: str, root_path: str, patterns: List[str]) -> bool:
    rel_path = os.path.relpath(path, root_path).replace("\\", "/")

    for pattern in patterns:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        if fnmatch.fnmatch(rel_path, f"{pattern}/*"):
            return True
        if fnmatch.fnmatch(os.path.basename(rel_path), pattern):
            return True

    return False


# =========================
# Tree Builder
# =========================

def build_tree(
    path: str,
    root_path: str,
    ignore_patterns: List[str]
) -> Optional[Node]:

    if path != root_path and is_ignored(path, root_path, ignore_patterns):
        return None

    name = Path(path).name or Path(root_path).resolve().name

    node = Node(
        name=name,
        path=path,
        is_dir=os.path.isdir(path)
    )

    if node.is_dir:
        try:
            for item in sorted(os.listdir(path)):
                child_path = os.path.join(path, item)
                child = build_tree(child_path, root_path, ignore_patterns)
                if child:
                    node.children.append(child)
        except PermissionError:
            pass

    return node


# =========================
# Tree Rendering
# =========================

def render_tree(node: Node, indent: str = "", is_last: bool = True):
    connector = "└── " if is_last else "├── "
    print(indent + connector + node.name)

    new_indent = indent + ("    " if is_last else "│   ")

    for i, child in enumerate(node.children):
        render_tree(
            child,
            new_indent,
            i == len(node.children) - 1
        )


def render_tree_to_lines(
    node: Node,
    indent: str = "",
    is_last: bool = True,
    lines: Optional[List[str]] = None
) -> List[str]:

    if lines is None:
        lines = []

    connector = "└── " if is_last else "├── "
    lines.append(indent + connector + node.name)

    new_indent = indent + ("    " if is_last else "│   ")

    for i, child in enumerate(node.children):
        render_tree_to_lines(
            child,
            new_indent,
            i == len(node.children) - 1,
            lines
        )

    return lines


# =========================
# Serialization
# =========================

def node_to_dict(node: Node) -> dict:
    return {
        "name": node.name,
        "path": node.path,
        "type": node.type,
        "size": node.size,
        "children": [node_to_dict(child) for child in node.children]
    }


def save_tree_to_json(root_node: Node, filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(node_to_dict(root_node), f, indent=2)


def save_tree_to_layout(root_node: Node, root_path: str, filename: str):
    lines = render_tree_to_lines(root_node)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"[{Path(root_path).resolve().name}]\n")
        for line in lines:
            f.write(line + "\n")


# =========================
# User Input
# =========================

def ask_yes_no(prompt: str) -> bool:
    while True:
        value = input(prompt).strip().lower()
        if value in ("y", "n"):
            return value == "y"
        print("Please enter 'y' or 'n'.")


# =========================
# Entry Point
# =========================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filesystem Snapshot Tool")
    parser.add_argument(
        "--ignore",
        type=str,
        nargs="*",
        default=[],
        help="Additional patterns to ignore (space-separated)"
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Display layout in console"
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Export layout to text file (layout.txt)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Export layout to JSON file (layout.json)"
    )
    
    args = parser.parse_args()

    # Determine output modes
    if args.console or args.text or args.json:
        show_console = args.console
        export_text = args.text
        export_json = args.json
    else:
        show_console = ask_yes_no("Display layout in console? (y/n): ")
        export_text = ask_yes_no("Export layout to text file? (y/n): ")
        export_json = ask_yes_no("Export layout to JSON file? (y/n): ")

    if not any([show_console, export_text, export_json]):
        raise SystemExit("No output selected. Exiting.")

    root_path = os.path.abspath(".")
    ignore_patterns = load_gitignore(root_path)
    
    # Add CLI-provided patterns
    if args.ignore:
        ignore_patterns.extend(args.ignore)

    root_node = build_tree(root_path, root_path, ignore_patterns)

    if not root_node:
        raise SystemExit("Failed to build filesystem tree.")

    if show_console:
        print(f"\nFilesystem layout for: {root_path}\n")
        render_tree(root_node)

    if export_text:
        save_tree_to_layout(root_node, root_path, "layout.txt")

    if export_json:
        save_tree_to_json(root_node, "layout.json")

    print("\nDone.")
