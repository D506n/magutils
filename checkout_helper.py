import argparse
import sys
from typing import TypedDict

import git
import orjson
import pathspec


class Args:
    source_branch: str
    no_ask: bool


class Config(TypedDict):
    branches: dict[str, str]
    allow_branch_migration: list[str]
    ignore_paths: list[str]


repo = git.Repo('.')

with open('checkout.json', 'r', encoding='utf-8') as f:
    config: Config = orjson.loads(f.read())

args_parser = argparse.ArgumentParser()
args_parser.add_argument('-m', '--migration', type=str, default='main>demo')
args_parser.add_argument('-y', '--no-ask', action='store_true', default=False)
args: Args = args_parser.parse_args()
source, target = args.migration.split('>')
source_branch = [b for b in repo.branches if b.name == source][0]
target_branch = [b for b in repo.branches if b.name == target][0]


def check_allow_migration(source: git.Head, target: git.Head):
    migration = f'{source.name}>{target.name}'
    if migration not in config['allow_branch_migration']:
        raise ValueError(f'Недопустимая миграция: {migration}'
        '\nСписок доступных миграций: \n'
        f'{"\n".join(config["allow_branch_migration"])}')
    if not args.no_ask:
        user_check = input(f'Начинаем миграцию {migration}. Вы уверены?(y/n): ')
        if user_check.lower() != 'y':
            print('Миграция отменена')
            sys.exit(1)
    else:
        print(f'Начинаем миграцию {migration}.')


def get_difflist(source: git.Head, target: git.Head):
    diffs = source.commit.diff(target.commit)
    ignore_spec = pathspec.PathSpec.from_lines(
        'gitwildmatch', config['ignore_paths'])
    result: list[git.Diff] = []
    for diff in diffs:
        if ignore_spec.match_file(diff.a_path):
            continue
        result.append(diff)
    print('Изменения в файлах для переноса:')
    for diff in result:
        print(f'\t{diff.a_path}->{diff.b_path} | {diff.change_type}')
    if not args.no_ask:
        usercheck = input('Вы уверены, что хотите перенести'
                          ' изменения этих файлов?(y/n): ')
        if usercheck.lower() != 'y':
            print('Миграция отменена')
            sys.exit(1)
    return result


def run_checkout(source: git.Head, target: git.Head, diffs: list[git.Diff]):
    current_branch = repo.active_branch
    repo.git.checkout(target)
    paths: list[str] = []
    to_del: list[str] = []
    to_commit: list[str] = []
    for diff in diffs:
        if diff.change_type == 'D':
            to_del.append(diff.a_path)
            to_commit.append(diff.a_path)
        else:
            paths.append(diff.b_path or diff.a_path)
            to_commit.append(diff.b_path or diff.a_path)
    print(repo.git.checkout(source.name, '--', *paths))
    if to_del:
        print(repo.git.rm('--cached', *to_del))
        print(repo.git.rm(*to_del))
    repo.git.add(*to_commit)
    commit_msg = f'Перенёс изменения {source.name}->{target.name}'
    repo.git.commit('-m', commit_msg)
    print(f'Создан коммит: {target.commit.hexsha}'
          f'\nКомментарий: {commit_msg}')
    repo.git.checkout(current_branch)


if __name__ == '__main__':
    check_allow_migration(source_branch, target_branch)
    diffs = get_difflist(source_branch, target_branch)
    run_checkout(source_branch, target_branch, diffs)