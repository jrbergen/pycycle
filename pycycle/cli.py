# -*- coding: utf-8 -*-
from __future__ import print_function

from pathlib import Path
from typing import Optional

import click
import crayons
import os
import sys

# local imports
from pycycle.__version__ import __version__
from pycycle.projectimportgraph import ProjectImportGraph

IGNORE_PATTERN_SEP: str = ','


def format_help(_help: str) -> str:
    """Formats the help string."""
    additional_help = """
    Examples:
        Get the circular imports in current project:
        $ {0}
        Look for circular imports in another project
        $ {1}
        Ignore specific directories when looking for circular import
        $ {2}
        Get verbose output
        $ {3}

Options:""".format(
        crayons.red('pycycle --here'),
        crayons.red('pycycle --source /home/user/workspace/awesome_project'),
        crayons.red('pycycle --source /home/user/workspace/awesome_project --ignore some_dir,some_dir2'),
        crayons.red('pycycle --source /home/user/workspace/awesome_project --verbose'),
    )

    _help = _help.replace('Options:', additional_help)

    return _help


@click.group(invoke_without_command=True)
@click.option('--verbose', is_flag=True, default=False, help="Verbose output.")
@click.option('--here', is_flag=True, default=False, help="Try to find cycles in the current project.")
@click.option('--source', default='', help="Try to find cycles in the path provided.", type=str)
@click.option('--ignore', default=None, help="Comma separated directory names that will be ignored during analysis.")
@click.option('--encoding', default='utf-8', help="Change encoding with which the project is read.")
@click.option('--force-rootfile', default='', help="Force to start building of the ast import tree at a file with this filename.",
              type=str)
@click.option('--skipfail', is_flag=True, default=False,
              help="Flag to disable the raising of any exceptions occuring during parsing.")
@click.option('--help', is_flag=True, default=None, help="Show this message then exit.")
@click.version_option(prog_name=crayons.yellow('pycycle'), version=__version__)
@click.pass_context
def cli(ctx: click.core.Context,
        verbose: bool = False,
        source: str = '',
        here: bool = False,
        ignore: Optional[str] = None,
        encoding: str = 'utf-8',
        force_rootfile: Optional[str] = None,
        skipfail: bool = False,
        help: bool = False) -> None:

    ignore_cliargs: set[str] = set() if ignore is None else set(ignore.split(IGNORE_PATTERN_SEP))

    if ctx.invoked_subcommand is None:

        source: Path = Path(source)
        if source:
            source = source.absolute()
            click.echo(crayons.yellow(
                'Target source provided: {}'.format(source)))
        elif here:
            source = Path(os.getcwd())
        else:
            # Display help to user, if no commands were passed.
            click.echo(format_help(ctx.get_help()))
            sys.exit(0)

        if not source:
            click.echo(crayons.red(
                'No project provided. Provide either --here or --source.'))

        if not source.exists():
            click.echo(crayons.red('Source file/directory does not exist.'), err=True)
            sys.exit(1)
        elif source.is_file():
            click.echo(crayons.red("A source file was passed; using it's parent directory"))
            source = source.parent
        elif not source.is_dir():
            click.echo(crayons.red('Source was neither a file nor directory.'), err=True)
            sys.exit()

        project = ProjectImportGraph(encoding=encoding,
                                     rootfile=force_rootfile,
                                     verbose=verbose,
                                     skipfail=skipfail,
                                     ignore_dirnames=ignore_cliargs)
        root_node = project.read_project(source)


        click.echo(crayons.yellow(
            'ProjectReader successfully transformed to AST, checking imports for cycles..'))

        if project.check_if_cycles_exist(root_node):
            click.echo(crayons.red('Cycle Found :('))
            result = project.get_cycle_path(root_node)
            click.echo(crayons.red(result))
            click.echo(crayons.green("Finished."))
            sys.exit(1)
        else:
            click.echo(crayons.green(('No worries, no cycles here!')))
            click.echo(crayons.green(
                'If you think some cycle was missed, please open an Issue on Github.'))
            click.echo(crayons.green("Finished."))
            sys.exit(0)


if __name__ == '__main__':
    cli()
