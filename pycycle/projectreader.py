from __future__ import annotations

import _ast
import ast
import re
import sys
from pathlib import Path
from typing import Optional, Union

import click
import crayons
from pycycle.filenode import FileNode

REGEX_RELATIVE_PATTERN: re.Pattern = re.compile(r'from .')
EXT_PY: str = '.py'


class ProjectReader:
    DEFAULT_IGNORE_DIRNAMES: tuple[str, ...] = ("__pycache__", "env", "venv", ".hg", ".svn", ".git", ".tox")

    def __init__(self,
                 encoding: str = 'utf-8',
                 skipfail: bool = False,
                 rootfile: Optional[str] = None,
                 ignore_dirnames: Optional[set[str]] = None,
                 verbose: bool = False):

        self.encoding: str = encoding
        self.ignore_dirs: set[str] = self.get_ignore_dirs(ignore_dirnames=ignore_dirnames)
        self.verbose: bool = verbose
        self.skipfail: bool = skipfail
        self.nodes: dict[Path, FileNode] = dict()
        self.curnode: Optional[FileNode] = None
        self.rootfile: str = self.get_rootfile(rootfile)

    def update_curnode_from_path(self, full_path: Path, file_name: str):
        if full_path not in self.nodes:
            self.nodes[full_path] = FileNode(file_name[:-3], full_path=full_path)
        self.curnode = self.nodes[full_path]

    def handle_import_abs(self,
                          ast_node,
                          root_path: Path,
                          full_path: Path):
        for subnode in ast_node.names:
            if not subnode.name:
                continue

            path_to_module = self.get_path_from_package_name(root_path, subnode.name)

            if path_to_module in self.nodes:
                new_node = self.nodes[path_to_module]
            else:
                new_node = FileNode(subnode.name,
                                    full_path=path_to_module)

                self.nodes[path_to_module] = new_node

            new_node.is_imported_from[full_path].append(ast_node.lineno)
            self.curnode.add(new_node)
            print(f"Temporary breakpoint in {__name__}")

    def handle_func_definitions(self, ast_node):
        self.curnode.func_defs[ast_node.name] = ast_node.lineno

    def handle_import_from(self,
                           ast_node,
                           root_path: Path,
                           full_path: Path,
                           curdir: Path,
                           lines: list[str]):

        current_path: Path = root_path
        if 0 <= ast_node.lineno - 1 < len(lines):
            print(lines[ast_node.lineno - 1])
            if REGEX_RELATIVE_PATTERN.findall(lines[ast_node.lineno - 1]):
                current_path = curdir

        path_to_module = self.get_path_from_package_name(current_path, ast_node.module)

        if path_to_module in self.nodes:
            new_node = self.nodes[path_to_module]
        else:
            new_node = FileNode(name=ast_node.module, full_path=path_to_module)
            self.nodes[path_to_module] = new_node

        for obj_import in ast_node.names:
            if ast_node.lineno not in self.curnode.func_imports:
                self.curnode.func_imports[ast_node.lineno] = [obj_import.name]
            else:
                self.curnode.func_imports[ast_node.lineno].append(obj_import.name)

        new_node.is_imported_from[full_path].append(ast_node.lineno)
        self.curnode.add(new_node)

    def walk_ast_and_update_cur_node(self,
                                     file_data,
                                     curdir: Path,
                                     lines: list[str],
                                     root_path: Path,
                                     full_path: Path):

        if self.verbose:
            click.echo(crayons.yellow(f'Trying to parse: $ROOT_PATH/{full_path.relative_to(root_path)}'))

        for ast_node in ast.walk(ast.parse(file_data)):

            if isinstance(ast_node, ast.Import) and ast_node.names:

                self.handle_import_abs(ast_node=ast_node,
                                       root_path=root_path,
                                       full_path=full_path)

            elif isinstance(ast_node, ast.ImportFrom) and ast_node.module:

                self.handle_import_from(ast_node=ast_node,
                                        root_path=root_path,
                                        full_path=full_path,
                                        curdir=curdir, lines=lines)

            elif isinstance(ast_node, (ast.ClassDef, ast.FunctionDef)):

                self.handle_func_definitions(ast_node=ast_node)

    def get_all_project_files(self, root_path: Path):
        allpaths = list(root_path.rglob(f'*{EXT_PY}'))
        if self.rootfile:
            new_allpaths = []
            found = []
            for path in allpaths:
                if path.is_dir() or self.rootfile != path.name:
                    new_allpaths.append(path)
                else:
                    click.echo(f"Found rootfile: $ROOTPATH/{path.relative_to(root_path)}..")
                    found.append(path)
            if not found:
                click.echo(f"Error: no file with name {self.rootfile!r} as passed via the --rootfile parameter was found.")
                sys.exit(1)
            elif len(found) > 1:
                click.echo(f"Error: multiple files found with filename {self.rootfile!r} as passed via the --rootfile parameter.")
                sys.exit(1)
            return found + new_allpaths
        else:
            return allpaths

    def read_project(self, root_path: Path):
        """
        Reads project into an AST and transforms imports into Nodes
        :param root_path: string
        :return: FileNode
        """

        root_node: Union[FileNode, None] = None
        errors: list[str] = []
        full_path: Path
        dirs: list[str]
        files: list[str]
        file_data: str
        lines: list[str]
        tree: _ast.Module

        # traverse root directory, and list directories as dirs and files as files
        for full_path in self.get_all_project_files(root_path=root_path):

            if set(full_path.parent.parts).intersection(self.ignore_dirs):
                if self.verbose:
                    click.echo(f"Ignored directory {full_path}")
                continue

            curdir = full_path.parent
            file_name = full_path.name

            with open(full_path, "r", encoding=self.encoding) as f:

                try:
                    # fails on empty files
                    file_data = f.read()
                    lines = file_data.splitlines()

                    self.update_curnode_from_path(full_path=full_path, file_name=file_name)

                    if not root_node:
                        root_node = self.curnode

                    self.walk_ast_and_update_cur_node(file_data=file_data,
                                                      curdir=curdir,
                                                      lines=lines,
                                                      root_path=root_path,
                                                      full_path=full_path)
                except Exception as e:
                    if self.skipfail:
                        raise
                    errors.append(e.args[0])
                    click.echo(crayons.yellow(f'Parsing of file failed: {full_path!r}'))

        if errors:
            if self.verbose:
                print("ERRORS:\n")
                for ifile, err in enumerate(errors):
                    print(f"Error for file number {ifile}: {err}")
            click.echo(crayons.red(' '.join(['There were errors during the operation.',
                                             'Note that this fork of PyCycle is no longer',
                                             'compatible with Python 3'])
                                   )
                       )
        root_node.imports = sorted(root_node.imports, key=lambda x: x.num_imports, reverse=True)
        return root_node

    @staticmethod
    def get_path_from_package_name(curpath: Path, pkg: str) -> Path:
        if not pkg or not curpath:
            return Path()
        modules = pkg.split(".")
        return curpath.joinpath(*modules).with_suffix(EXT_PY)

    @staticmethod
    def get_import_context(node: FileNode):
        """
        Go backs up the graph to the import that started this possible cycle,
        and gets the import line number
        :param node:
        :return: int
        """
        name: str = node.name
        seen: set[FileNode] = set()
        while node.parent and node.parent.parent:
            node = node.parent
            if node in seen or (node.parent and node.parent.name == name):
                break
            seen.add(node)

        # Should never fail because we take the full_path of the parent. And as the parent imports this child
        # there should at least be one number in the array
        print(f"Temporary breakpoint in {__name__}")
        return node.is_imported_from[node.parent.full_path][0]

    def check_if_cycles_exist(self, root: FileNode) -> bool:
        """
        Goes through all nodes and looks for cycles, takes python import logic into account
        :param root:
        :return: bool
        """
        previous: Union[None, FileNode] = None
        queue: list[FileNode] = [root]
        while queue:
            self.curnode = queue.pop()
            if self.curnode.marked > 1:
                return not self.curnode.is_in_context

            for item in self.curnode.imports:

                # Mark the current node as parent, so that we could trace the path from this node to the start node.
                item.parent = self.curnode
                if item.marked and previous:

                    # This is a possible cycle, but maybe the import statement that started this all is under the function
                    # definition that is required
                    import_that_started = self.get_import_context(item)
                    for lineno, imports in previous.func_imports.items():
                        for import_obj in imports:
                            # Compare the function definition line with the import line
                            if import_obj in item.func_defs\
                                    and import_that_started > item.func_defs[import_obj]:
                                item.is_in_context = True
                previous = item
                queue.append(item)

            self.curnode.marked += 1

        return False

    def format_path(self, path: list[FileNode]) -> str:
        """
        Format the cycle with colors
        :param path:
        :return: str
        """
        if len(path) > 1:
            result = [crayons.yellow(path[0].name)]

            previous = path[0]
            for item in path[1:]:
                result.append(' -> ')
                result.append(crayons.yellow(item.name))
                result.append(': Line ')
                result.append(crayons.cyan(str(item.is_imported_from[previous.full_path][0])))
                previous = item
            result.append(' =>> ')

            result.append(crayons.magenta(path[0].name))
            return ''.join(str(x) for x in result)
        else:
            return ''

    def get_cycle_path(self,
                       rootnode: FileNode,
                       acc: Optional[list] = None,
                       seen: Optional[set[Path]] = None) -> str:
        seen = set() if seen is None else seen
        acc = [] if acc is None else acc

        for import_item in rootnode:
            if import_item.full_path in seen:
                return self.format_path(acc)
            seen.add(import_item.full_path)
            if import_item.imports:
                acc.append(import_item)
                return self.get_cycle_path(import_item, acc, seen)

        return ''

    @staticmethod
    def get_rootfile(rootfile: Optional[str] = None) -> str:
        return str(Path(rootfile).with_suffix(EXT_PY)) if rootfile else ''

    @classmethod
    def get_ignore_dirs(cls, ignore_dirnames: Optional[Union[set[str], tuple[str, ...]]]) -> set[str]:
        ignore_dirnames = set() if ignore_dirnames is None else ignore_dirnames
        return ignore_dirnames.union(ProjectReader.DEFAULT_IGNORE_DIRNAMES)
