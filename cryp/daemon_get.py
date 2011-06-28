import os.path

from . import gui
from .storage import Storage

def get_options():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("request", metavar="STR",
        help="A name of requested password")
    return ap

def main():
    options = get_options().parse_args()
    stor = Storage(os.path.expanduser('~/.cache/cryp/daemon'))
    if gui.PasswordGui(stor).check_pass():
        for uid, title, date in stor.titles():
            if title == options.request:
                data = stor.entry(uid)
                data = data[data.index('\n')+1:]
                data = data.replace('$PASSWORD', stor.secret(uid))
                print(data)
                break
