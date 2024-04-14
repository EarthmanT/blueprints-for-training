import os
import re
import yaml
import shutil
import pathlib
import subprocess


def get_path(joined):
    return pathlib.Path(joined).as_posix()


github_dir = get_path(os.path.join(os.path.expanduser('~'), 'Documents', 'Github'))
old_blueprints_path = get_path(os.path.join(github_dir, 'blueprints-for-training.bak'))
new_blueprints_path = get_path(os.path.join(github_dir, 'blueprints-for-training'))

NEW_BLUEPRINTS = []
START_BLUEPRINT = 'blueprints_for_training_generic_blueprints_test_generate_blueprint-2569.yaml'
start_yet = False


def recurse_directory(path='.'):
    TOTAL_FILES = 0
    for entry in os.listdir(path):
        if start_yet == False and entry != START_BLUEPRINT:
            continue
        elif entry == START_BLUEPRINT:
            start_yet = True
        TOTAL_FILES += 1
        full_path = get_path(os.path.join(path, entry))
        if os.path.isdir(full_path):
            # recurse_directory(full_path)
            continue
        print(f'Adding {entry}.')
        shutil.copyfile(full_path, get_path(os.path.join(new_blueprints_path, entry)))
        subprocess.run(f'git add {entry}'.split(' '))
        if TOTAL_FILES >= 100000:
            subprocess.run(f'git commit -m \"Adding-chunk-{TOTAL_FILES}\"'.split(" "))
            subprocess.run(['git', 'push'])
            TOTAL_FILES = 0


def remove_cloudify(path='.'):
    TOTAL_FILES = 0
    for entry in os.listdir(path):
        if not entry.endswith('.yaml'):
            continue
        delete = False
        full_path = get_path(os.path.join(path, entry))
        with open(full_path, 'r') as out:
            if 'cloudify' in out.readline():
                delete = True
                TOTAL_FILES += 1
        if delete:
            os.remove(full_path)
            subprocess.run(f'git rm {entry}'.split(' '))
        if TOTAL_FILES >= 100000:
            subprocess.run(f'git commit -m \"Removing-chunk-{TOTAL_FILES}\"'.split(" "))
            subprocess.run(['git', 'push'])
            TOTAL_FILES = 0


if __name__ == "__main__":
    # remove_cloudify(new_blueprints_path)
    recurse_directory(old_blueprints_path)
