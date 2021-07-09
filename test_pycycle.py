from __future__ import print_function
import os

from pycycle.projectreader import ProjectReader

def test_get_path_from_package_name():
    raise NotImplementedError("Tests not yet updated...")

    func = ProjectReader.get_path_from_package_name

    assert func('/test/one/two', 'some.package') == '/test/one/two/some/package.py'
    assert func('', 'some.package') == ''
    assert func('/', None) == ''
    assert func(None, 'some.package') == ''
    assert func('/test/', 'some_package') == '/test/some_package.py'


def test_format_path():
    raise NotImplementedError("Tests not yet updated...")
    pass


def test_simple_project():
    raise NotImplementedError("Tests not yet updated...")
    project = {'path': os.path.abspath('./tests/_projects/a_references_b_b_references_a'),
               'has_cycle': True,
               'result': 'b_module -> a_module: Line 1 =>> b_module'}

    root_node = ProjectReader.read_project(project['path'])
    assert root_node != None
    assert ProjectReader.check_if_cycles_exist(
        root_node) == project['has_cycle']
    assert ProjectReader.get_cycle_path(root_node, acc=[], seen=set()) == project['result']


def test_no_circular_imports():
    raise NotImplementedError("Tests not yet updated...")
    project = {'path': os.path.abspath('./tests/_projects/has_no_circular_imports'),
               'has_cycle': False,
               'result': ''}
    root_node = ProjectReader.read_project(project['path'])
    assert root_node is not None
    assert ProjectReader.check_if_cycles_exist(
        root_node) == project['has_cycle']
    assert ProjectReader.get_cycle_path(root_node, acc=[], seen=set()) == ''


def test_large_circle():
    raise NotImplementedError("Tests not yet updated...")
    project = {'path': os.path.abspath('./tests/_projects/large_circle'),
               'has_cycle': True,
               'result': 'a_module.a_file -> a_module.b_module.b_file: Line 1 -> c_module.c_file: Line 1 -> d_module.d_file: Line 1 =>> a_module.a_file'}

    root_node = ProjectReader.read_project(project['path'])
    assert root_node is not None
    assert ProjectReader.check_if_cycles_exist(
        root_node) == project['has_cycle']
    assert ProjectReader.get_cycle_path(root_node, acc=[], seen=set()) == project['result']


def test_large_no_circle():
    raise NotImplementedError("Tests not yet updated...")
    project = {'path': os.path.abspath('./tests/_projects/large_without_circle'),
               'has_cycle': False,
               'result': ''}
    root_node = ProjectReader.read_project(project['path'])
    assert root_node is not None
    assert ProjectReader.check_if_cycles_exist(
        root_node) == project['has_cycle']
    assert ProjectReader.get_cycle_path(root_node, acc=[], seen=set()) == ''



def test_relative_imports():
    raise NotImplementedError("Tests not yet updated...")
    project = {'path': os.path.abspath('./tests/_projects/relative_imports'),
               'has_cycle': True,
               'result': 'myapp.models -> managers: Line 1 =>> myapp.models'}
    root_node = ProjectReader.read_project(project['path'])
    assert root_node is not None
    assert ProjectReader.check_if_cycles_exist(
        root_node) == project['has_cycle']
    assert ProjectReader.get_cycle_path(root_node, acc=[], seen=set()) == project['result']


def test_import_context():
    project = {'path': os.path.abspath('./tests/_projects/large_circle_context'),
               'has_cycle': False,
               'result': ''}
    root_node = ProjectReader.read_project(project['path'])
    assert root_node is not None
    assert ProjectReader.check_if_cycles_exist(
        root_node) == project['has_cycle']