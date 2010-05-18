#!/usr/bin/python
import string

import pygtk
pygtk.require('2.0')

import gtk, gobject, glib

from .storage import Storage

PASSWORD_CHARS = string.digits + string.letters
PASSWORD_LENGTH = 20

class Application(object):
    def __init__(self):
        self.win = gtk.Window()
        self.win.connect('delete-event', lambda *a: gtk.main_quit())
        self.win.connect('key-press-event', self.windowkey)
        self.win.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_UTILITY)
        self.win.show()
        self.store = Storage()

    def check_pass(self):
        if self.store.created:
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
            if self.store.open(entry.get_text()):
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
        self.store.create(a.get_text())
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
        for tup in self.store.titles(): #uid, title, date
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
        self.note.get_buffer().set_text(self.store.entry(uid))
        self.password.set_text(self.store.secret(uid))

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
                self.store.update_entry(self.recname, data)
                self.store.update_secret(self.recname, pw)
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
                    self.store.remove(self.recname)
                    self.fill_main()
                dlg.hide()
            elif event.keyval == gtk.keysyms.p:
                if hasattr(self, 'recname'):
                    tx = self.store.secret(self.recname)
                else:
                    uid = self.list.get_model()[self.list.get_cursor()[0]][0]
                    tx = self.store.secret(uid)
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
