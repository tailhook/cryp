#!/usr/bin/python
import hashlib
import random
import uuid
import os.path
import glob

from Crypto.Cipher import AES, Blowfish

randbytes = os.urandom

def crypt(k1, k2, data):
    one = AES.new(k1, AES.MODE_ECB)
    two = Blowfish.new(k2, Blowfish.MODE_ECB)
    return two.encrypt(one.encrypt(data))

def decrypt(k1, k2, data):
    one = AES.new(k1, AES.MODE_ECB)
    two = Blowfish.new(k2, Blowfish.MODE_ECB)
    return one.decrypt(two.decrypt(data))

class Storage(object):
    def __init__(self):
        self.root = os.path.join(os.path.expanduser('~'), 'note', 'pass')
        self.keyfile = os.path.join(self.root, '.key')
        self.blocksize = 4096
        self.keysize1 = 32
        self.keysize2 = 4096
        self.keysize = self.keysize1 + self.keysize2

    def open(self, value):
        k2 = value
        k1 = hashlib.sha256(k2).digest()
        with open(self.keyfile, 'rb') as f:
            data = decrypt(k1, k2, f.read(self.blocksize + self.keysize + 64))
        if hashlib.sha512(data[:-64]).digest() == data[-64:]:
            key = data[self.blocksize:-64]
            self.key1 = key[:self.keysize1]
            self.key2 = key[self.keysize1:]
            return True
        else:
            return False

    def create(self, value):
        assert not os.path.exists(self.keyfile)
        vec = randbytes(self.blocksize)
        key = randbytes(self.keysize)
        k2 = value
        k1 = hashlib.sha256(k2).digest()
        with open(self.keyfile, 'wb') as f:
            f.write(crypt(k1, k2, vec+key+hashlib.sha512(vec+key).digest()))
        self.key1 = key[:self.keysize1]
        self.key2 = key[self.keysize1:]
        return True

    def titles(self):
        """Yields uid, title, description for each item in store"""
        for i in glob.glob(os.path.join(self.root, '*a')):
            data = self.read(i)
            val = data.splitlines()[0]
            uid = os.path.basename(i)[:-1]
            yield uid, val, data

    def entry(self, uid):
        return self.read(os.path.join(self.root, uid+'a'))

    def secret(self, uid):
        return self.read(uid+'b')

    def update_entry(self, data):
        self.write(self.recname + 'a', data)

    def update_secret(self, value):
        self.write(self.recname + 'b', value)

    def remove(self, uid):
        os.unlink(os.path.join(self.root, uid+'b'))
        os.unlink(os.path.join(self.root, uid+'a'))

    def write(self, name, data):
        vec = randbytes(self.blocksize)
        with open(os.path.join(self.root, name), 'wb') as f:
            tail = len(data) % self.blocksize
            if tail:
                data += '\x00'*(self.blocksize-tail)
            f.write(crypt(self.key1, self.key2, vec + data))

    def read(self, name):
        with open(os.path.join(self.root, name), 'rb') as f:
            res = decrypt(self.key1, self.key2, f.read())[self.blocksize:]
            try:
                return res[:res.index('\x00')]
            except IndexError:
                return res

    @property
    def created(self):
        return os.path.exists(self.keyfile)

def main():
    import getpass
    store = Storage()
    while True:
        value = getpass.getpass('Master password: ')
        if not value:
            returnR
        if store.open(value):
            break
    while True:
        index = {}
        for idx, (uid, title, _) in enumerate(store.titles()):
            print "{0:d}. {1}".format(idx+1, title)
            index[idx+1] = uid
        val = raw_input("Record number or (q)uit: ")
        try:
            uid = index[int(val)]
        except (KeyError, ValueError):
            if val in 'qx' or not val:
                break
        while True:
            what = raw_input("Show (d)escription or (p)assword or (r)return: ")
            if what == 'r':
                break
            elif what == 'd':
                print store.entry(uid)
            elif what == 'p':
                print store.secret(uid)


if __name__ == '__main__':
    main()
