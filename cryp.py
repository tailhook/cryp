#!/usr/bin/python
import hashlib, random, uuid
import string
import os.path, glob

import pygtk
pygtk.require('2.0')

import gtk, gobject, glib
from Crypto.Cipher import AES, Blowfish

ROOT = os.path.join(os.path.expanduser('~'), 'note', 'pass')
KEYFILE = os.path.join(ROOT, '.key')
BLOCKSIZE = 4096
KEYSIZE1 = 32
KEYSIZE2 = 4096
KEYSIZE = KEYSIZE1 + KEYSIZE2
PASSWORD_CHARS = string.digits + string.letters
PASSWORD_LENGTH = 20

randbytes = os.urandom

def crypt(k1, k2, data):
    one = AES.new(k1, AES.MODE_ECB)
    two = Blowfish.new(k2, Blowfish.MODE_ECB)
    return two.encrypt(one.encrypt(data))

def decrypt(k1, k2, data):
    one = AES.new(k1, AES.MODE_ECB)
    two = Blowfish.new(k2, Blowfish.MODE_ECB)
    return one.decrypt(two.decrypt(data))

class Application(object):
    def __init__(self):
        self.win = gtk.Window()
        self.win.connect('delete-event', lambda *a: gtk.main_quit())
        self.win.connect('key-press-event', self.windowkey)
        self.win.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_UTILITY)
        self.win.show()

    def check_pass(self):
        if os.path.exists(KEYFILE):
            return self._check_pass()
        else:
            return self._create_pass()

    def _check_pass(self):
        dlg = gtk.Dialog(title=u"Enter password", flags=gtk.DIALOG_MODAL,
            buttons=(
            gtk.STOCK_OK, gtk.RESPONSE_OK,
            gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            ))
        entry = gtk.Entry()
        entry.props.visibility = False
        dlg.get_content_area().pack_start(entry)
        dlg.show_all()
        while dlg.run() == gtk.RESPONSE_OK:
            k2 = entry.get_text()
            k1 = hashlib.sha256(k2).digest()
            with open(KEYFILE, 'rb') as f:
                data = decrypt(k1, k2, f.read(BLOCKSIZE+KEYSIZE+64))
            if hashlib.sha512(data[:-64]).digest() == data[-64:]:
                key = data[BLOCKSIZE:-64]
                self.key1 = key[:KEYSIZE1]
                self.key2 = key[KEYSIZE1:]
                dlg.hide()
                return True
        else:
            return False

    def _create_pass(self):
        dlg = gtk.Dialog(title=u"Create password", flags=gtk.DIALOG_MODAL,
            buttons=(
            gtk.STOCK_OK, gtk.RESPONSE_OK,
            gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            ))
        dlg.set_transient_for(self.win)
        a = gtk.Entry()
        a.props.visibility = False
        b = gtk.Entry()
        b.props.visibility = False
        dlg.get_content_area().pack_start(a)
        dlg.get_content_area().pack_start(b)
        dlg.show_all()
        while not a.get_text() or a.get_text() != b.get_text():
            if dlg.run() != gtk.RESPONSE_OK:
                return False
        vec = randbytes(BLOCKSIZE)
        key = randbytes(KEYSIZE)
        k2 = a.get_text()
        k1 = hashlib.sha256(k2).digest()
        with open(KEYFILE, 'wb') as f:
            f.write(crypt(k1, k2, vec+key+hashlib.sha512(vec+key).digest()))
        self.key1 = key[:KEYSIZE1]
        self.key2 = key[KEYSIZE1:]
        dlg.hide()
        return True

    def update_search(self, widget):
        val = widget.get_text().lower()
        mod = self.list.get_model()
        mod.clear()
        for i in self.all:
            if val in i[2].lower():
                mod.append(i)

    def fill_main(self):
        if self.win.child:
            self.win.remove(self.win.child)
        vbox = gtk.VBox()
        self.search = gtk.Entry()
        self.search.connect('changed', self.update_search)
        vbox.pack_start(self.search, expand=False)
        lmod = gtk.ListStore(str, str, str)
        self.all = all = []
        for i in glob.glob(os.path.join(ROOT, '*a')):
            data = self.read(i)
            val = data.splitlines()[0]
            tup = (os.path.basename(i)[:-1], val, data)
            lmod.append(tup)
            all.append(tup)
        self.list = gtk.TreeView(lmod)
        self.list.connect('row-activated', self.select_rec)
        ren = gtk.CellRendererText()
        col = gtk.TreeViewColumn("Title")
        col.pack_start(ren)
        col.add_attribute(ren, 'text', 1)
        self.list.append_column(col)
        sw = gtk.ScrolledWindow()
        sw.add(self.list)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.list.set_hadjustment(sw.get_hadjustment())
        self.list.set_vadjustment(sw.get_vadjustment())
        vbox.pack_start(sw, expand=True)
        self.win.add(vbox)
        vbox.show_all()

    def fill_rec(self):
        if self.win.child:
            self.win.remove(self.win.child)
        vbox = gtk.VBox()
        self.note = gtk.TextView()
        sw = gtk.ScrolledWindow()
        sw.add(self.note)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.note.emit('set-scroll-adjustments',
            sw.get_hadjustment(), sw.get_vadjustment())
        vbox.pack_start(sw, expand=True)
        self.password = gtk.Entry()
        self.password.props.visibility = False
        vbox.pack_start(self.password, expand=False)
        self.win.add(vbox)
        vbox.show_all()

    def select_rec(self, widget, path, col):
        uid = widget.get_model()[path][0]
        self.fill_rec()
        self.recname = uid
        self.note.get_buffer().set_text(self.read(os.path.join(ROOT, uid+'a')))
        self.password.set_text(self.read(uid+'b'))

    def windowkey(self, widget, event):
        if event.state == gtk.gdk.CONTROL_MASK:
            if event.keyval == gtk.keysyms.n:
                self.recname = str(uuid.uuid4())
                self.fill_rec()
            elif event.keyval == gtk.keysyms.s:
                if not hasattr(self, 'recname'):
                    self.search.grab_focus()
                    return False
                buf = self.note.get_buffer()
                data = buf.get_text(*buf.get_bounds())
                pw = self.password.get_text()
                self.write(self.recname + 'a', data)
                self.write(self.recname + 'b', pw)
                del self.recname
                self.fill_main()
            elif event.keyval == gtk.keysyms.r:
                del self.recname
                self.fill_main()
            elif event.keyval == gtk.keysyms.j:
                if hasattr(self, 'recname'):
                    if not self.password.get_text():
                        self.password.set_text(''.join(
                            random.choice(PASSWORD_CHARS)
                            for i in xrange(PASSWORD_LENGTH)))
            elif event.keyval == gtk.keysyms.d:
                dlg = gtk.Dialog(title="Delete record?", flags=gtk.DIALOG_MODAL,
                    buttons=(
                        gtk.STOCK_YES, gtk.RESPONSE_YES,
                        gtk.STOCK_NO, gtk.RESPONSE_NO,
                        ))
                dlg.set_transient_for(self.win)
                if dlg.run() == gtk.RESPONSE_YES:
                    os.unlink(os.path.join(ROOT, self.recname+'a'))
                    os.unlink(os.path.join(ROOT, self.recname+'b'))
                    self.fill_main()
                dlg.hide()
            elif event.keyval == gtk.keysyms.p:
                if hasattr(self, 'recname'):
                    tx = self.read(self.recname + 'b')
                else:
                    uid = self.list.get_model()[self.list.get_cursor()[0]][0]
                    tx = self.read(uid + 'b')
                cb = gtk.Clipboard()
                cb.set_text(tx)
            elif event.keyval == gtk.keysyms.e:
                if hasattr(self, 'recname'):
                    self.password.grab_focus()
                else:
                    self.select_rec(self.list, *self.list.get_cursor())
            else:
                return False
            return True
        if event.keyval == gtk.keysyms.Escape:
            del self.recname
            self.fill_main()
            return True
        return False

    def write(self, name, data):
        vec = randbytes(BLOCKSIZE)
        with open(os.path.join(ROOT, name), 'wb') as f:
            tail = len(data) % BLOCKSIZE
            if tail:
                data += '\x00'*(BLOCKSIZE-tail)
            f.write(crypt(self.key1, self.key2, vec + data))

    def read(self, name):
        with open(os.path.join(ROOT, name), 'rb') as f:
            res = decrypt(self.key1, self.key2, f.read())[BLOCKSIZE:]
            try:
                return res[:res.index('\x00')]
            except IndexError:
                return res

    def show_icon(self):
        self.icon = gtk.status_icon_new_from_stock(
            gtk.STOCK_DIALOG_AUTHENTICATION)

    def hide_icon(self):
        self.icon.set_visible(False)

    def run(self):
        if not self.check_pass():
            return False
        self.fill_main()
        self.show_icon()
        gtk.main()
        self.hide_icon()

if __name__ == '__main__':
    Application().run()
