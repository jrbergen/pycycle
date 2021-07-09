from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterator, Optional, Union


class FileNode:

    def __init__(self,
                 name: str,
                 full_path: Path,
                 imports: Optional[list[FileNode]] = None,
                 line_no=None):
        self.name: str = name
        if not imports:
            self.imports = []
        else:
            self.imports = imports

        self.is_imported_from: dict[Path, list] = defaultdict(list)
        self.full_path: Path = full_path
        self.marked: int = 0
        self.parent: Union[FileNode, None] = None
        self.func_imports: dict = dict()
        self.func_defs: dict = dict()
        self.is_in_context: bool = False

    @property
    def num_imports(self) -> int:
        return len(self.imports)

    def __iter__(self) -> Iterator[FileNode]:
        return iter(self.imports)

    def add(self, item):
        self.imports.append(item)

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(num_imports={self.num_imports})"



