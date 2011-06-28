#!/usr/bin/python
import string
import uuid
import random

from gi.repository import Gtk, GObject, GLib, Gdk

from .storage import Storage

PASSWORD_CHARS = string.digits + string.ascii_letters
PASSWORD_LENGTH = 20

class Application(object):
    def __init__(self):
        self.win = Gtk.Window()
        self.win.connect('delete-event', lambda *a: Gtk.main_quit())
        self.win.connect('key-press-event', self.windowkey)
        self.win.show()
        self.store = Storage()

    def check_pass(self):
        if self.store.created:
            return self._check_pass()
        else:
            return self._create_pass()

    def _check_pass(self):
        dlg = Gtk.Dialog(title="Enter password", flags=Gtk.DialogFlags.MODAL,
            buttons=(
            Gtk.STOCK_OK, Gtk.ResponseType.OK,
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            ))
        entry = Gtk.Entry()
        entry.props.visibility = False
        dlg.get_content_area().pack_start(entry, True, True, 8)
        dlg.show_all()
        while dlg.run() == Gtk.ResponseType.OK:
            if self.store.open(entry.get_text().encode('utf-8')):
                dlg.hide()
                return True
        else:
            return False

    def _create_pass(self):
        dlg = Gtk.Dialog(title="Create password", flags=Gtk.DialogFlags.MODAL,
            buttons=(
            Gtk.STOCK_OK, Gtk.ResponseType.OK,
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            ))
        dlg.set_transient_for(self.win)
        a = Gtk.Entry()
        a.props.visibility = False
        b = Gtk.Entry()
        b.props.visibility = False
        dlg.get_content_area().pack_start(a,
            expand=True, fill=True, padding=0)
        dlg.get_content_area().pack_start(b)
        dlg.show_all()
        while not a.get_text() or a.get_text() != b.get_text():
            if dlg.run() != Gtk.ResponseType.OK:
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
        if self.win.get_child():
            self.win.remove(self.win.get_child())
        vbox = Gtk.VBox()
        self.search = Gtk.Entry()
        self.search.connect('changed', self.update_search)
        vbox.pack_start(self.search, False, False, 0)
        lmod = Gtk.ListStore(str, str, str)
        self.all = all = []
        for tup in self.store.titles(): #uid, title, date
            lmod.append(tup)
            all.append(tup)
        self.list = Gtk.TreeView(model=lmod)
        self.list.connect('row-activated', self.select_rec)
        ren = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("Title")
        col.pack_start(ren, False)
        col.add_attribute(ren, 'text', 1)
        self.list.append_column(col)
        sw = Gtk.ScrolledWindow()
        sw.add(self.list)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(sw, True, True, 0)
        self.win.add(vbox)
        vbox.show_all()

    def fill_rec(self):
        if self.win.get_child():
            self.win.remove(self.win.get_child())
        vbox = Gtk.VBox()
        self.note = Gtk.TextView()
        sw = Gtk.ScrolledWindow()
        sw.add(self.note)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(sw, True, True, 0)
        self.password = Gtk.Entry()
        self.password.props.visibility = False
        vbox.pack_start(self.password, False, False, 0)
        self.win.add(vbox)
        vbox.show_all()

    def select_rec(self, widget, path, col):
        uid = widget.get_model()[path][0]
        self.fill_rec()
        self.recname = uid
        self.note.get_buffer().set_text(self.store.entry(uid))
        self.password.set_text(self.store.secret(uid))

    def windowkey(self, widget, event):
        if event.state == Gdk.ModifierType.CONTROL_MASK:
            if event.keyval == Gdk.KEY_n:
                self.recname = str(uuid.uuid4())
                self.fill_rec()
            elif event.keyval == Gdk.KEY_s:
                if not hasattr(self, 'recname'):
                    self.search.grab_focus()
                    return False
                buf = self.note.get_buffer()
                a, b = buf.get_bounds()
                data = buf.get_text(a, b, True)
                pw = self.password.get_text()
                self.store.update_entry(self.recname, data)
                self.store.update_secret(self.recname, pw)
                del self.recname
                self.fill_main()
            elif event.keyval == Gdk.KEY_r:
                del self.recname
                self.fill_main()
            elif event.keyval == Gdk.KEY_j:
                if hasattr(self, 'recname'):
                    if not self.password.get_text():
                        self.password.set_text(''.join(
                            random.choice(PASSWORD_CHARS)
                            for i in range(PASSWORD_LENGTH)))
            elif event.keyval == Gdk.KEY_d:
                dlg = Gtk.Dialog(title="Delete record?", flags=Gtk.DialogFlags.MODAL,
                    buttons=(
                        Gtk.STOCK_YES, Gtk.ResponseType.YES,
                        Gtk.STOCK_NO, Gtk.ResponseType.NO,
                        ))
                dlg.set_transient_for(self.win)
                uid = self.list.get_model()[self.list.get_cursor()[0]][0]
                tv = Gtk.TextView(editable=False)
                tv.get_buffer().set_text(self.store.entry(uid))
                tv.show()
                dlg.get_content_area().pack_start(tv, True, True, 0)
                if dlg.run() == Gtk.ResponseType.YES:
                    self.store.remove(uid)
                    self.fill_main()
                dlg.hide()
            elif event.keyval == Gdk.KEY_p:
                if hasattr(self, 'recname'):
                    tx = self.store.secret(self.recname)
                else:
                    uid = self.list.get_model()[self.list.get_cursor()[0]][0]
                    tx = self.store.secret(uid)
                cb = Gtk.Clipboard.get(Gdk.atom_intern("CLIPBOARD", True))
                cb.set_text(tx, len(tx.encode('utf-8')))
            elif event.keyval == Gdk.KEY_e:
                if hasattr(self, 'recname'):
                    self.password.grab_focus()
                else:
                    self.select_rec(self.list, *self.list.get_cursor())
            else:
                return False
            return True
        if event.keyval == Gdk.KEY_Escape:
            del self.recname
            self.fill_main()
            return True
        return False

    def show_icon(self):
        self.icon = Gtk.StatusIcon.new_from_stock(
            Gtk.STOCK_DIALOG_AUTHENTICATION)

    def hide_icon(self):
        self.icon.set_visible(False)

    def run(self):
        if not self.check_pass():
            return False
        self.fill_main()
        self.show_icon()
        Gtk.main()
        self.hide_icon()

def main():
    Application().run()

if __name__ == '__main__':
    main()
