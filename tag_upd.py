import os
from argparse import ArgumentParser
from pathlib import Path
from re import compile

parser = ArgumentParser()
tag_reg = compile(r'version = \".+?\"')
parser.add_argument('-t', '--tag', type=str)

args = parser.parse_args()

tag = args.tag

file = Path('./pyproject.toml')

data = file.read_text(encoding='utf-8')

new_data = tag_reg.sub(f'version = "{tag}"', data)

file.write_text(new_data)
os.system(f'git add {file} && git commit -m \'set tag to {tag}\' && git push')

print(f'Version set to {tag}')