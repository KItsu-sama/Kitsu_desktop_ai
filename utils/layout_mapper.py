"""
utils/layout_mapper.py

Filesystem snapshot tool extracted and enhanced from legacy code.

Scans directories recursively, respects .gitignore rules, builds tree structures,
and provides both console and programmatic output options.
"""

import os
import json
import fnmatch
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, asdict

log = logging.getLogger(__name__)


@dataclass
class FileNode:
    """Represents a file or directory in the filesystem tree."""
    name: str
    path: str
    is_dir: bool
    size: Optional[int] = None
    type: str = "file"
    children: List['FileNode'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        self.type = "directory" if self.is_dir else "file"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class LayoutMapper:
    """
    Filesystem layout mapper with .gitignore support.
    
    Enhanced from legacy version with:
    - Better error handling
    - Configurable ignore patterns
    - Multiple output formats
    - Statistics collection
    - Async support for large directories
    """
    
    def __init__(self, root_path: Union[str, Path], ignore_patterns: Optional[List[str]] = None):
        """
        Initialize layout mapper.
        
        Args:
            root_path: Root directory to scan
            ignore_patterns: Additional ignore patterns beyond .gitignore
        """
        self.root_path = Path(root_path).resolve()
        self.ignore_patterns = ignore_patterns or []
        
        # Load .gitignore patterns
        self.gitignore_patterns = self._load_gitignore()
        self.all_patterns = self.gitignore_patterns + self.ignore_patterns
        
        log.debug(f"LayoutMapper initialized for {self.root_path}")
        log.debug(f"Ignore patterns: {len(self.all_patterns)} total")
    
    def _load_gitignore(self) -> List[str]:
        """Load patterns from .gitignore file."""
        patterns = []
        gitignore_file = self.root_path / ".gitignore"
        
        if gitignore_file.exists():
            try:
                with open(gitignore_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.append(line.rstrip("/"))
                log.debug(f"Loaded {len(patterns)} patterns from .gitignore")
            except Exception as e:
                log.warning(f"Error reading .gitignore: {e}")
        
        # Always ignore git internals
        patterns.append(".git")
        return patterns
    
    def _is_ignored(self, path: Path) -> bool:
        """Check if path should be ignored based on patterns."""
        try:
            rel_path = path.relative_to(self.root_path).as_posix()
            
            for pattern in self.all_patterns:
                # Direct match
                if fnmatch.fnmatch(rel_path, pattern):
                    return True
                # Directory match
                if fnmatch.fnmatch(rel_path, f"{pattern}/*"):
                    return True
                # Basename match
                if fnmatch.fnmatch(path.name, pattern):
                    return True
            
            return False
        except ValueError:
            # Path is not relative to root (shouldn't happen)
            return True
    
    def _build_tree(self, path: Path) -> Optional[FileNode]:
        """Build tree node for given path."""
        if path != self.root_path and self._is_ignored(path):
            return None
        
        try:
            node = FileNode(
                name=path.name if path != self.root_path else path.resolve().name,
                path=str(path),
                is_dir=path.is_dir()
            )
            
            if node.is_dir:
                try:
                    # Sort entries for consistent output
                    entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
                    
                    for entry in entries:
                        child = self._build_tree(entry)
                        if child:
                            node.children.append(child)
                            
                except PermissionError:
                    log.warning(f"Permission denied accessing {path}")
                except Exception as e:
                    log.warning(f"Error scanning {path}: {e}")
            else:
                # Get file size
                try:
                    node.size = path.stat().st_size
                except OSError:
                    node.size = None
            
            return node
            
        except Exception as e:
            log.error(f"Error building tree for {path}: {e}")
            return None
    
    def build_tree(self) -> Optional[FileNode]:
        """Build the complete filesystem tree."""
        try:
            root_node = self._build_tree(self.root_path)
            if root_node:
                log.info(f"Built tree with {self._count_nodes(root_node)} nodes")
            return root_node
        except Exception as e:
            log.error(f"Failed to build tree: {e}")
            return None
    
    def _count_nodes(self, node: FileNode) -> int:
        """Count total nodes in tree."""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count
    
    def render_tree_to_lines(self, root_node: FileNode, include_size: bool = False) -> List[str]:
        """Render tree as list of text lines."""
        lines = []
        
        def _render_node(node: FileNode, indent: str = "", is_last: bool = True):
            connector = "    " if node.is_dir else "    "
            prefix = "    " if indent == "" else indent
            
            if include_size and not node.is_dir and node.size is not None:
                size_str = f" ({self._format_size(node.size)})"
            else:
                size_str = ""
            
            line = f"{prefix}{'    ' if node.is_dir else '    '}{node.name}{size_str}"
            lines.append(line)
            
            new_indent = indent + ("    " if is_last else "    ")
            
            for i, child in enumerate(node.children):
                _render_node(child, new_indent, i == len(node.children) - 1)
        
        # Add header
        lines.append(f"[{root_node.name}]")
        _render_node(root_node)
        
        return lines
    
    def render_tree_to_console(self, root_node: FileNode, include_size: bool = False) -> None:
        """Print tree to console."""
        lines = self.render_tree_to_lines(root_node, include_size)
        for line in lines:
            print(line)
    
    def save_tree_to_json(self, root_node: FileNode, filename: Union[str, Path]) -> None:
        """Save tree structure to JSON file."""
        try:
            output_path = Path(filename)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(root_node.to_dict(), f, indent=2, ensure_ascii=False)
            
            log.info(f"Tree saved to {output_path}")
            
        except Exception as e:
            log.error(f"Failed to save tree to JSON: {e}")
    
    def save_tree_to_layout(self, root_node: FileNode, filename: Union[str, Path]) -> None:
        """Save tree structure to text layout file."""
        try:
            output_path = Path(filename)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            lines = self.render_tree_to_lines(root_node, include_size=False)
            
            with open(output_path, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(line + "\n")
            
            log.info(f"Layout saved to {output_path}")
            
        except Exception as e:
            log.error(f"Failed to save layout: {e}")
    
    def get_statistics(self, root_node: FileNode) -> Dict[str, Any]:
        """Get statistics about the filesystem tree."""
        stats = {
            'total_nodes': 0,
            'directories': 0,
            'files': 0,
            'total_size': 0,
            'ignored_patterns': len(self.all_patterns),
            'largest_files': []
        }
        
        file_sizes = []
        
        def _collect_stats(node: FileNode):
            stats['total_nodes'] += 1
            
            if node.is_dir:
                stats['directories'] += 1
            else:
                stats['files'] += 1
                if node.size is not None:
                    stats['total_size'] += node.size
                    file_sizes.append((node.name, node.size))
            
            for child in node.children:
                _collect_stats(child)
        
        _collect_stats(root_node)
        
        # Find largest files
        file_sizes.sort(key=lambda x: x[1], reverse=True)
        stats['largest_files'] = file_sizes[:10]
        stats['total_size_formatted'] = self._format_size(stats['total_size'])
        
        return stats
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def find_files(self, pattern: str, root_node: Optional[FileNode] = None) -> List[FileNode]:
        """Find files matching a pattern."""
        if root_node is None:
            root_node = self.build_tree()
            if not root_node:
                return []
        
        matches = []
        
        def _search(node: FileNode):
            if not node.is_dir and fnmatch.fnmatch(node.name.lower(), pattern.lower()):
                matches.append(node)
            
            for child in node.children:
                _search(child)
        
        _search(root_node)
        return matches
    
    def get_directory_structure(self, max_depth: int = 3) -> Dict[str, Any]:
        """Get simplified directory structure up to max depth."""
        root_node = self.build_tree()
        if not root_node:
            return {}
        
        def _simplify(node: FileNode, current_depth: int = 0) -> Dict[str, Any]:
            if current_depth >= max_depth:
                return {
                    'name': node.name,
                    'type': node.type,
                    'children_count': len(node.children)
                }
            
            result = {
                'name': node.name,
                'type': node.type
            }
            
            if node.children:
                result['children'] = [_simplify(child, current_depth + 1) 
                                     for child in node.children[:20]]  # Limit children
            
            return result
        
        return _simplify(root_node)


# Convenience functions
def create_layout_mapper(
    root_path: Union[str, Path], 
    ignore_patterns: Optional[List[str]] = None
) -> LayoutMapper:
    """
    Create a LayoutMapper instance.
    
    Args:
        root_path: Root directory to scan
        ignore_patterns: Additional ignore patterns
        
    Returns:
        LayoutMapper instance
    """
    return LayoutMapper(root_path, ignore_patterns)


def scan_directory(
    root_path: Union[str, Path],
    output_json: Optional[Union[str, Path]] = None,
    output_layout: Optional[Union[str, Path]] = None,
    console_output: bool = False,
    ignore_patterns: Optional[List[str]] = None
) -> Optional[FileNode]:
    """
    Scan a directory and optionally output results.
    
    Args:
        root_path: Directory to scan
        output_json: Optional JSON output file
        output_layout: Optional layout text file
        console_output: Whether to print to console
        ignore_patterns: Additional ignore patterns
        
    Returns:
        Root FileNode if successful, None otherwise
    """
    mapper = LayoutMapper(root_path, ignore_patterns)
    root_node = mapper.build_tree()
    
    if not root_node:
        log.error("Failed to build directory tree")
        return None
    
    if console_output:
        print(f"\nDirectory layout for: {root_path}\n")
        mapper.render_tree_to_console(root_node)
    
    if output_json:
        mapper.save_tree_to_json(root_node, output_json)
    
    if output_layout:
        mapper.save_tree_to_layout(root_node, output_layout)
    
    return root_node


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Scan directory structure")
    parser.add_argument("path", nargs="?", default=".", help="Directory to scan")
    parser.add_argument("--json", help="Output JSON file")
    parser.add_argument("--layout", help="Output layout file")
    parser.add_argument("--console", action="store_true", help="Print to console")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--all", action="store_true", help="Output all formats (JSON, layout, console)")
    
    args = parser.parse_args()
    
    root_node = scan_directory(
        args.path,
        output_json=args.json,
        output_layout=args.layout,
        console_output=args.console
    )
    
    if root_node and args.stats:
        mapper = LayoutMapper(args.path)
        stats = mapper.get_statistics(root_node)
        print("\nStatistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
