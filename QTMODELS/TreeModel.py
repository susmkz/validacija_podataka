#!/usr/bin/python3
# -*- coding: utf-8 -*-
from PyQt5 import QtCore


class TreeItem(object):
    """
    Klasa za definiranje tree (stablo) strukture podataka. Definira čvor u stablu.
    Potreban za definiranje tree strukture za izbor programa mjerenja na postajama.

    self._parent --> referencira parent čvor (takodjer TreeItem objekt)
    self._children --> LISTA djece (child itemi su TreeItem objekti)
    self._data --> kontenjer za podatke čvora (npr, lista, dict...)
    """
    def __init__(self, data, parent=None):
        """ Konstruktor klase."""
        self._parent = parent
        self._data = data
        self._children = []
        if self._parent is not None:
            # ako je parent zadan, radi čuvanja konzistencije, moramo dodati
            # trenutnu instancu u popis djece parenta. tj. link od djeteta do parenta
            # moramo upotpuniti linkom od parenta do djeteta.
            self._parent._children.append(self)

    def child(self, row):
        """ Za zadani red, vrati child čvor. """
        return self._children[row]

    def child_count(self):
        """ Vrati ukupan broj child čvorova """
        return len(self._children)

    def childNumber(self):
        """
        Vrati indeks pod kojim se ova instanca objekta nalazi u listi djece
        parent objekta
        """
        if self._parent is not None:
            return self._parent._children.index(self)
        return 0

    def columnCount(self):
        """
        TreeItem objekt se inicijalizira sa "spremnikom" podataka (data).
        Ova funkcija vraca broj podataka u spremniku.
        """
        return len(self._data)

    def data(self, column):
        """
        funkcija koja dohvaca element iz "spremnika" podataka

        promjeni implementaciju ako se promjeni 'priroda' spremnika
        npr. ako je spremnik integer vrijednost ovo nece raditi
        """
        return self._data[column]

    def parent(self):
        """ Vrati instancu parent objekta (TreeItem)."""
        return self._parent

    def __repr__(self):
        """
        print() reprezentacija objekta
        promjeni implementaciju ako se promjeni 'priroda' spremnika
        npr. ako je spremnik integer vrijednost ovo nece raditi
        """
        return str(self.data(0))


class ModelDrva(QtCore.QAbstractItemModel):
    """
    Specificna implementacija QtCore.QAbstractItemModel za tree listu stanica i programa
    mjerenja. Model nije editablian.

    Za inicijalizaciju modela bitno je prosljediti root item neke tree strukture
    koja se sastoji od TreeItem instanci.
    """
    def __init__(self, root=None, parent=None):
        """ Konstruktor klase. root je korjenski čvor neke strukture stabla (TreeItem)"""
        super(ModelDrva, self).__init__(parent)
        if isinstance(root, TreeItem):
            self.rootItem = root # postavi korjenski čvor
        else:
            # slucaj kada nije zadan korjenski čvor, stvori predefinirani čvor
            self.rootItem = TreeItem(['stanice', None, None, None], parent=None)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Funkcija vraca indeks u modelu za zadani red, stupac i parent
        """
        if parent.isValid() and parent.column() != 0:
            return QtCore.QModelIndex()
        parentItem = self.getItem(parent)
        childItem = parentItem.child(row)
        if childItem:
            # napravi index za red, stupac i child
            return self.createIndex(row, column, childItem)
        else:
            # vrati prazan QModelIndex
            return QtCore.QModelIndex()

    def getItem(self, index):
        """
        BITNA QT FUNKCIJA. Funckija vraca objekt pod indeksom index, ili rootItem ako indeks
        nije valjan
        """
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item
        return self.rootItem

    def rowCount(self, parent=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Preko nje view dohvaća broj redova u tablici. Broj redova
        je broj children objekata unutar parenta
        """
        parentItem = self.getItem(parent)
        return parentItem.child_count()

    def columnCount(self, parent=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Preko nje view dohvaća broj stupaca u tablici.

        ['Stanica/komponenta', 'Formula', 'Id', 'Usporedno']
        """
        return 4

    def flags(self, index):
        """
        BITNA QT FUNKCIJA. Preko nje view definira dozvoljene akcije pojedine
        "ćelije" u tablici.
        """
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """
        BITNA QT FUNKCIJA. Preko nje view definira što i kako prikazati za pojedinu
        "ćeliju" u tablici. Određujemo prikaz vrijednosti i stila.

        ['Stanica/komponenta', 'Formula', 'Id', 'Usporedno']
        """
        # ako je indeks pogrešno zadan nemamo što raditi
        if not index.isValid():
            return None
        # dohvaćamo vrijednost pod indeksom
        item = self.getItem(index)
        # DISPLAY ROLE - sto prikazujemo u ćeliji
        if role == QtCore.Qt.DisplayRole:
            if index.column() == 0:
                return item.data(0)
            elif index.column() == 1:
                return item.data(3)
            elif index.column() == 2:
                return item.data(2)
            elif index.column() == 3:
                return item.data(1)

    def parent(self, index):
        """
        BITNA QT FUNKCIJA. Vrati parent od TreeItem objekta pod datim indeksom.
        Ako TreeItem nema parenta, ili ako je indeks nevalidan, vrati
        defaultni QModelIndex (ostatak modela ga zanemaruje)
        """
        if not index.isValid():
            return QtCore.QModelIndex()
        childItem = self.getItem(index)
        parentItem = childItem.parent()
        if parentItem == self.rootItem:
            return QtCore.QModelIndex()
        else:
            return self.createIndex(parentItem.childNumber(), 0, parentItem)

    def headerData(self, section, orientation, role):
        """
        BITNA QT FUNKCIJA. Preko nje view definira nazive redaka i stupaca u tablici.
        ['Stanica/komponenta', 'Formula', 'Id', 'Usporedno']
        """
        headeri = ['Stanica/komponenta', 'Formula', 'Id', 'Usporedno']
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return headeri[section]
        return None

