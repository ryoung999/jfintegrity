from os.path import isfile
from getpass import getpass


def get_config(file='.access_token'):
    if not isfile(file):
        config = getpass(prompt=f'Enter {file}: ')
    else:
        with open(file, 'r') as f:
            config = f.read()

    return config.strip()