import yaml


def loadConfig(path='config.yaml'):
    with open(path, 'r') as file:
        return yaml.safe_load(file)
