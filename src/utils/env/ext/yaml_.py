from pathlib import Path

try:
    import yaml as yaml_lib
except ImportError:
    raise ImportError('PyYAML not installed!'
                      ' Run `pip install pyyaml` to get yaml lib.')


def yaml(file_path: Path, field_path: str):
    if isinstance(file_path, str):
        file_path = Path(file_path)

    def factory(ctx: dict):
        if str(field_path) not in ctx.keys():
            with open(file_path) as f:
                ctx[str(file_path)] = yaml_lib.safe_load(f)

        data: dict = ctx[str(file_path)]
        path = field_path.split('.')
        while path:
            key = path[0]
            path = path[1:]
            try:
                data = data[key]
            except KeyError as e:
                raise KeyError(f'Key {e} not found in {data}')
        return data

    return factory