import getpass

import yaml

from . import storage

def dump(file):
    import getpass
    store = storage.Storage()
    while True:
        value = getpass.getpass('Master password: ')
        if not value:
            return
        if store.open(value.encode('utf-8')):
            break
    for uid, _, description in store.titles():
        yaml.dump({
            'key': uid,
            'description': description,
            'secret': store.secret(uid)
            }, file, default_flow_style=True,
            explicit_start=True, explicit_end=True)

def restore(file):
    if getpass.getpass("All files will be overwritten.\n"
        "Also it's your responsibility to clean password storage before use.\n"
        "Continue? (must type \"Yes\")\n") != "Yes":
        return
    store = storage.Storage()
    while True:
        one = getpass.getpass('New master password: ')
        if not one:
            return
        two = getpass.getpass('Confirm master password: ')
        if one != two:
            print("Passwords do not match")
            continue
        if len(one) < 8:
            print("More characters needed (probably a lot more!)")
            continue
        break
    store.create(one.encode('utf-8'))
    for item in yaml.load_all(file):
        store.update_entry(item['key'], item['description'])
        store.update_secret(item['key'], item['secret'])

def main():
    import optparse
    op = optparse.OptionParser()
    op.add_option('-r', '--restore',
        help="Restore backup",
        dest="action", action="store_const", const="restore")
    op.add_option('-d', '--dump',
        help="Dump backup (it's unencoded, please use openssl or whatever to"
             " encode dump)",
        dest="action", action="store_const", const="dump")
    options, args = op.parse_args()
    if len(args) > 1:
        op.error("No more than one argument expected")
    if options.action == 'dump':
        if args:
            with open(args[0], 'wb') as file:
                dump(file)
        else:
            import sys
            dump(sys.stdout)
    elif options.action == 'restore':
        if args:
            with open(args[0], 'rb') as file:
                restore(file)
        else:
            import sys
            restore(sys.stdin)
    else:
        op.error("Wrong or unspecified action")

if __name__ == '__main__':
    main()
