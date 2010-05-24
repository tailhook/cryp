from __future__ import absolute_import

import dbus
from dbus.service import (
    Object as DbusObject,
    method as dbus_method,
    signal as dbus_signal,
    )
import gobject
import uuid
import yaml

SERVICE = 'org.freedesktop.Secret.Service'
COLLECTION = 'org.freedesktop.Secret.Collection'
ITEM = 'org.freedesktop.Secret.Item'
SESSION = 'org.freedesktop.Secret.Session'
PROMPT = 'org.freedesktop.Secret.Prompt'
PROPERTIES = 'org.freedesktop.DBus.Properties'

class NotSupported(dbus.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.NotSupported'

class Session(DbusObject):
    def __init__(self, bus, sid, parent):
        self.sid = sid
        self.parent = parent
        super(Session, self).__init__(bus,
            '/org/freedesktop/secrets/session/{0}'.format(sid))

    @dbus_method(dbus_interface=SESSION)
    def Close(self):
        self.parent.sessions.pop(self.sid)

class Collection(DbusObject):
    SUPPORTS_MULTIPLE_OBJECT_PATHS = True

    def __init__(self, bus, name, store):
        self.name = name
        self.store = store
        super(Collection, self).__init__(bus,
            '/org/freedesktop/secrets/collection/{0}'.format(name))

    @dbus_method(dbus_interface=PROPERTIES,
        in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        assert interface_name == COLLECTION, interface_name
        return dict((uid, Item(self, uid))
            for uid, title, description in self.store.titles())

    @dbus_method(dbus_interface=COLLECTION,
        in_signature="a{sv}(oayay)b", out_signature="oo")
    def CreateItem(self, properties, secret, replace):
        # TODO: check ``replace`` flag
        try:
            num = int(self.store.entry('0'))
        except KeyError:
            num = 1
        num += 1
        self.store.update_entry('0', str(num))
        props = dict(properties)
        secret = bytes(bytearray(secret[2]))
        id = str(num)
        self.store.update_entry(id, yaml.dump(props))
        self.store.update_secret(id, secret)
        return Item(self, id), '/'

class Item(DbusObject):
    def __new__(self, collection, id):
        if not hasattr(collection, '_items'):
            collection._items = {}
        if id in collection._items:
            return collection._items[id]
        val = super(Item, self).__new__(self)
        collection._items[id] = val
        return val

    def __init__(self, collection, id):
        if hasattr(self, 'id'):
            # already initialized
            assert self.id == id
            return
        self.id = id
        self.collection = collection
        collection_path = next(iter(collection.locations))[1]
        super(Item, self).__init__(collection.connection,
            '{0}/{1}'.format(collection_path, id.replace('-', '_')))

    @dbus_method(dbus_interface=PROPERTIES,
        in_signature="ss", out_signature="v")
    def Get(self, interface, name):
        assert interface == 'org.freedesktop.Secret.Item'
        val = self.collection.store.entry(self.id)
        return yaml.load(val)[name]

class Service(DbusObject):
    def __init__(self, bus, store):
        self.collections = {
            'default': Collection(bus, 'login', store),
            }
        for k, v in self.collections.iteritems():
            v.add_to_connection(bus,
                '/org/freedesktop/secrets/aliases/{0}'.format(k))
        self.sessions = {}
        self.last_sid = 0
        super(Service, self).__init__(bus, '/org/freedesktop/secrets')

    @dbus_method(dbus_interface=SERVICE, sender_keyword='sender',
        in_signature='sv', out_signature='vo')
    def OpenSession(self, algorithm, input, sender):
        if algorithm != 'plain':
            raise NotSupported()
        else:
            self.last_sid += 1
            sid = self.last_sid
            sess = Session(self.connection, sid, self)
            self.sessions[sid] = sess
            return '', sess._object_path

    @dbus_method(dbus_interface=SERVICE,
        in_signature='s', out_signature='o')
    def ReadAlias(self, name):
        try:
            return next(iter(self.collections['default'].locations))[1]
        except KeyError:
            return '/'

    @dbus_method(dbus_interface=SERVICE,
        in_signature='a{ss}', out_signature='aoao')
    def SearchItems(self, input):
        found = []
        col = self.collections['default']
        for uid, _, data in col.store.titles():
            if uid == '0':
                continue
            info = yaml.load(data)
            attr = info.get('Attributes', {})
            for k, v in input.iteritems():
                if attr.get(k) != v:
                    break
            else:
                found.append(Item(col, uid))
        return found, []

    @dbus_method(dbus_interface=SERVICE,
        in_signature="ao", out_signature="aoo")
    def Unlock(self, objects):
        return objects, dbus.ObjectPath('/')

    @dbus_method(dbus_interface=SERVICE,
        in_signature="aoo", out_signature="a{o(oayay)}")
    def GetSecrets(self, objects, session):
        col = self.collections['default']
        res = {}
        for ob in objects:
            res[ob] = (session, '', col.store.secret(ob[ob.rindex('/')+1:]))
        return res

class Prompt(DbusObject):
    counter = 0
    def __init__(self, bus):
        self.__class__.counter += 1
        super(Prompt, self).__init__(bus,
            '/org/freedesktop/secrets/_prompts/{0}'.format(self.counter))

    @dbus_signal(dbus_interface=PROMPT, signature='s')
    def Prompt(self, window_id):
        print "PROMPT", window_id

    @dbus_signal(dbus_interface=PROMPT, signature='bv')
    def Completed(self, dismissed, result):
        pass

def serve(store):
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    name = dbus.service.BusName("org.freedesktop.secrets", bus)
    svc = Service(bus, store)
    gobject.MainLoop().run()

def main():
    import getpass
    import os.path
    from .storage import Storage
    store = Storage(path=os.path.join(os.path.expanduser('~'),
        '.config', 'cryp', 'local'))
    while True:
        value = getpass.getpass('Master password: ')
        if not value:
            return
        if store.open(value):
            break
    serve(store)

if __name__ == '__main__':
    main()
