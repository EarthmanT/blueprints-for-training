import os
import re
import yaml
import shutil
import pathlib

BLUEPRINT_YAML_TEMPLATE = {
    'tosca_definitions_version': 'cloudify_dsl_1_5',
    'imports': [
        'cloudify/types/types.yaml',
    ],
    'inputs': {},
    'node_templates': {}
}

CONCAT = 'concat'
GET_SYS = 'get_sys'
GET_INPUT = 'get_input'
GET_SECRET = 'get_secret'
GET_PROPERTY = 'get_property'
GET_ATTRIBUTE = 'get_attribute'
GET_CAPABILITY = 'get_capability'
GET_ATTRIBUTE_LIST = 'get_attribute_list'
GET_ENVIRONMENT_CAPABILITY = 'get_environment_capability'
INSTRINSIC_FUNCTIONS = [
    CONCAT,
    GET_SYS,
    GET_INPUT,
    GET_SECRET,
    GET_PROPERTY,
    GET_ATTRIBUTE,
    GET_CAPABILITY,
    GET_ATTRIBUTE_LIST,
    GET_ENVIRONMENT_CAPABILITY
]

def split_lines(string):
  return re.split(r'\r?\n', string)


class CloudifySafeDumper(yaml.SafeDumper):

    def increase_indent(self, flow=False, indentless=False):
        return super(CloudifySafeDumper, self).increase_indent(flow, False)

    def ignore_aliases(self, data):
        return True


def represent_intrinsic_function_args(args):
    if isinstance(args, list):
        new_list = []
        for item in args:
            if isinstance(item, str):
                item = f"'{item}'"
            new_list.append(item)
        args = new_list
    return args


def represent_intrinsic_functions(dumper, data):
    for fn in INSTRINSIC_FUNCTIONS:
        if fn in data:
            return dumper.org_represent_str(
                '{{ {fn}: {val} }}'.format(fn=fn, val=(represent_intrinsic_function_args(data[fn]))))
    return dumper.represent_dict(data)


def repr_str(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar(
            u'tag:yaml.org,2002:str', data, style='>')
    # elif any(not c.isalnum() for c in data):
    #     return dumper.represent_scalar('tag:yaml.org,2002:str', data, style="'")
    return dumper.org_represent_str(data)


yaml.SafeDumper.org_represent_str = yaml.SafeDumper.represent_str
yaml.add_representer(str, repr_str, Dumper=yaml.SafeDumper)
yaml.add_representer(
    dict, represent_intrinsic_functions, Dumper=yaml.SafeDumper)

def dos2unix(string):
    string = string.replace(r'\r', r'\n')
    string = string.encode()
    string = string.replace(b'\r\n', b'\n')
    return string



def create_new_cloudify_yaml(python_dict, blueprint):
    yaml_obj = yaml.dump(
        python_dict,
        Dumper=CloudifySafeDumper,
        default_flow_style=False,
        sort_keys=False,
        width=float('inf')
    )
    lines = yaml_obj.split('\n')
    for line_no in range(0, len(lines)):
        for fn in INSTRINSIC_FUNCTIONS:
            if fn in lines[line_no]:
                lines[line_no] = lines[line_no].replace("'", '')
                break
    new_yaml = ''
    for line in lines:
        if line in ['imports:', 'inputs:', 'node_templates:']:
            new_yaml += '\n'
            new_yaml += '{}\n'.format(line)
            new_yaml += '\n'
        elif re.match(r'^[\s]{2}[a-zA-Z]', line):
            new_yaml += '\n'
            new_yaml += '{}\n'.format(line)
        else:
            new_yaml += '{}\n'.format(line)
    with open(blueprint, 'wb') as outfile:
        outfile.write(dos2unix(new_yaml))


def get_path(joined):
    return pathlib.Path(joined).as_posix()


github_dir = get_path(os.path.join(os.path.expanduser('~'), 'Documents', 'Github'))
new_blueprints_path = get_path(os.path.join(github_dir, 'blueprints-for-training', 'blueprints'))
solutions = get_path(os.path.join(github_dir, 'hzp-eo-solutions'))

NEW_BLUEPRINTS = []

def list_files_recursive(path='.'):
    for entry in os.listdir(path):
        full_path = get_path(os.path.join(path, entry))
        if os.path.isdir(full_path):
            list_files_recursive(full_path)
        elif full_path.endswith('.yaml'):
            with open(full_path, 'r') as outf:
                line = outf.readline()
                if not line.startswith('tosca_def'):
                    continue
                elif full_path not in NEW_BLUEPRINTS:
                    NEW_BLUEPRINTS.append(full_path)


def filter_imports(imports):
    new_imports = []
    for item in imports:
        if not item.startswith('plugin:') and item not in [
                'nativeedge/types/types.yaml',
                'cloudify/types/types.yaml'] and item.endswith('.yaml'):
            new_imports.append(item)
    return new_imports


def recursive_merge(dict1, dict2):
    if dict1 == dict2:
        return dict1
    elif isinstance(dict1, str) and isinstance(dict2, str):
        return dict1 + dict2
    elif isinstance(dict1, int):
        return dict1
    try:
        merged = dict1.copy()
    except AttributeError:
        print(f'This line failed: {dict1} {dict2}.')
        raise
    if isinstance(dict1, dict) and isinstance(dict2, dict):
        for key, value in dict2.items():
            if key in merged:
                merged[key] = recursive_merge(merged[key], value)
            else:
                merged[key] = value
    elif isinstance(dict1, list) and isinstance(dict2, list):
        merged.extend([item for item in dict2 if item not in merged])
    else:
        pass
    return merged


def compile_new_blueprint(blueprint):
    CHANGED = False
    parent = get_path(pathlib.Path(blueprint).parent.absolute())
    with open(blueprint, 'r') as outf:
        try:
            content = yaml.safe_load(outf)
        except Exception:
            NEW_BLUEPRINTS.remove(blueprint)
            return
    if 'imports' in content:
        imports = filter_imports(content.get('imports'))
        if any(imports):
            for item in imports:
                filename = os.path.basename(item)
                absolute = get_path(os.path.join(parent, filename))
                if not os.path.exists(absolute):
                    absolute = get_path(os.path.join(parent, item))
                    if not os.path.exists(absolute):
                        print(f'Failed to resolve import {item} of {blueprint}.')
                        continue
                print(f'Blueprint {blueprint} has {absolute}')
                imported_content = {}
                with open(absolute, 'r') as adj_outf:
                    try:
                        imported_content = yaml.safe_load(adj_outf.read())
                    except Exception:
                        print(f'Skipping {absolute}')
                        continue
                content = recursive_merge(content, imported_content)
                CHANGED = True
        if CHANGED:
            new_path = get_path(os.path.join(new_blueprints_path, blueprint.replace(github_dir, "").replace("/", "_")))
            print(f'Gonna write a new file to {new_path}')
            create_new_cloudify_yaml(content, new_path)


if __name__ == "__main__":
    list_files_recursive(solutions)
    for blueprint in NEW_BLUEPRINTS:
        compile_new_blueprint(blueprint)
