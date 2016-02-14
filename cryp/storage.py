#!/usr/bin/python
import hashlib
import random
import uuid
import os.path
import glob

from ._cipher import aes_encrypt, aes_decrypt, bf_encrypt, bf_decrypt

randbytes = os.urandom

def crypt(k1, k2, data):
    return aes_encrypt(bf_encrypt(data, k2), k1)

def decrypt(k1, k2, data):
    return bf_decrypt(aes_decrypt(data, k1), k2)

class Storage(object):
    def __init__(self, path=None):
        if path is None:
            self.root = os.path.join(os.path.expanduser('~'), 'note', 'pass2')
        else:
            self.root = os.path.realpath(path)
        self.keyfile = os.path.join(self.root, '.key')
        self.blocksize = 4096
        self.keysize1 = 32
        self.keysize2 = 56
        self.keysize = self.keysize1 + self.keysize2
        self.keypad = 16 - self.keysize % 16

    def open(self, value):
        k2 = value[:56]
        k1 = hashlib.sha256(value).digest()
        with open(self.keyfile, 'rb') as f:
            datasize = self.blocksize + self.keysize + self.keypad + 64
            data = decrypt(k1, k2, f.read(datasize))
        if hashlib.sha512(data[:-64]).digest() == data[-64:]:
            key = data[self.blocksize:-64]
            self.key1 = key[:self.keysize1]
            self.key2 = key[self.keysize1:self.keysize1+self.keysize2]
            return True
        else:
            return False

    def create(self, value):
        assert not os.path.exists(self.keyfile)
        vec = randbytes(self.blocksize)
        key = randbytes(self.keysize)
        k2 = value[:56]
        k1 = hashlib.sha256(value).digest()
        with open(self.keyfile, 'wb') as f:
            pad = randbytes(self.keypad)
            body = vec+key+pad
            f.write(crypt(k1, k2, body+hashlib.sha512(body).digest()))
        self.key1 = key[:self.keysize1]
        self.key2 = key[self.keysize1:]
        return True

    def titles(self):
        """Yields uid, title, description for each item in store"""
        for i in glob.glob(os.path.join(self.root, '*a')):
            data = self.read(i).decode('utf-8')
            val = data.splitlines()[0] if data else '<empty>'
            uid = os.path.basename(i)[:-1]
            yield uid, val, data

    def entry(self, uid):
        try:
            return self.read(os.path.join(self.root, uid+'a')).decode('utf-8')
        except IOError:
            raise KeyError(uid)

    def secret(self, uid):
        try:
            return self.read(uid+'b').decode('utf-8')
        except IOError:
            raise KeyError(uid)

    def update_entry(self, id, data):
        self.write(id + 'a', data.encode("utf-8"))

    def update_secret(self, id, value):
        self.write(id + 'b', value.encode("utf-8"))

    def remove(self, uid):
        os.unlink(os.path.join(self.root, uid+'b'))
        os.unlink(os.path.join(self.root, uid+'a'))

    def write(self, name, data):
        vec = randbytes(self.blocksize)
        with open(os.path.join(self.root, name), 'wb') as f:
            tail = len(data) % self.blocksize
            if tail:
                data += b'\x00'*(self.blocksize-tail)
            f.write(crypt(self.key1, self.key2, vec + data))

    def read(self, name):
        with open(os.path.join(self.root, name), 'rb') as f:
            res = decrypt(self.key1, self.key2, f.read())[self.blocksize:]
            try:
                return res[:res.index(b'\x00')]
            except (IndexError, ValueError):
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
            return
        if store.open(value.encode('utf-8')):
            break
    while True:
        index = {}
        for idx, (uid, title, _) in enumerate(store.titles()):
            print("{0:d}. {1}".format(idx+1, title))
            index[idx+1] = uid
        val = input("Record number or (q)uit: ")
        try:
            uid = index[int(val)]
        except (KeyError, ValueError):
            if val in 'qx' or not val:
                break
        while True:
            what = input("Show (d)escription or (p)assword or (r)return: ")
            if what == 'r':
                break
            elif what == 'd':
                print(store.entry(uid))
            elif what == 'p':
                print(store.secret(uid))


if __name__ == '__main__':
    main()
