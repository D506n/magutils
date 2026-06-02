import subprocess
from argparse import ArgumentParser
from pathlib import Path
from re import compile

parser = ArgumentParser()
tag_reg = compile(r'version = \".+?\"')
parser.add_argument('-t', '--tag', type=str)
parser.add_argument('-m', '--message', type=str)

args = parser.parse_args()

tag = args.tag
msg = args.message

file = Path('./pyproject.toml')

data = file.read_text(encoding='utf-8')

new_data = tag_reg.sub(f'version = "{tag}"', data)

file.write_text(new_data)
subprocess.run(['git', 'add', '.'], check=True)
subprocess.run(['git', 'commit', '-m', msg], check=True)
subprocess.run(['git', 'push'], check=True)

print(f'Version set to {tag}')