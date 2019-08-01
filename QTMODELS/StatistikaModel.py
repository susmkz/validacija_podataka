#!/usr/bin/python3
# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui
from app.DOCUMENT.Session import Session


class StatistikaTablica(QtCore.QAbstractTableModel):
    """
    Klasa za model podataka statistike, provodi se samo na podacima na koje je
    primjenjena korekcija.
    """
    def __init__(self):
        super(StatistikaTablica, self).__init__()
        #inicijalizacija sa Session objektom - svi ucitani podaci na jednom mjestu.
        self._SESSION = Session({})

    ##################### QT MODEL FUNCTIONS - START ###########################
    def rowCount(self, parent=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Preko nje view dohvaća broj redova u tablici. Broj redova
        odgovara broju kanala u Session objektu
        """
        return len(self._SESSION.sviKanali)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Preko nje view dohvaća broj stupaca u tablici.
        Prikazujemo samo 5 stupca zbog smanjivanja podataka na ekranu:
            stupac 0 --> srednja vrijednost valjanih podataka korekcije
            stupac 1 --> standardna devijacija valjanih podataka korekcije
            stupac 2 --> minimalna vrijednost valjanih podataka korekcije
            stupac 3 --> maksimalna vrijednost valjanih podataka korekcije
            stupac 4 --> obuhvat podataka, valjani satni podaci korekcije
            stupac 5 --> broj valjanih minutnih podataka korekcije ispod 0
            stupac 6 --> broj minutnih podataka ispod LDL
        """
        return 7

    def flags(self, index):
        """
        BITNA QT FUNKCIJA. Preko nje view definira dozvoljene akcije pojedine
        "ćelije" u tablici.
        """
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role):
        """
        BITNA QT FUNKCIJA. Preko nje view definira što i kako prikazati za pojedinu
        "ćeliju" u tablici. Određujemo prikaz vrijednosti i stila.
        col:
        0 - average (samo OK flagiranih)
        1 - stdev (samo OK flagiranih)
        2 - min (samo OK flagiranih)
        3 - max (samo OK flagiranih)
        4 - obuhvat (satnih, samo OK flagiranih)
        5 - broj korekcija minutnih ispod 0 (samo OK flagiranih)
        6 - broj minutnih korekcija ispod LDL
        """
        # ako je indeks pogrešno zadan nemamo što raditi
        if not index.isValid():
            return None
        # dohvaćamo red i stupac indeksa
        row = index.row()
        col = index.column()
        # dohvacanje liste kanala i opisa iz sessiona
        kanali = self.session.sviKanali
        KANAL_DATASTORE = self.session.get_datastore(kanali[row])
        # DISPLAY ROLE - sto prikazujemo u ćeliji
        if role == QtCore.Qt.DisplayRole:
            if col == 0: #average
                return str(KANAL_DATASTORE.satni.get_valid_average())
            elif col == 1: #std
                return str(KANAL_DATASTORE.satni.get_valid_std())
            elif col == 2: #min
                return str(KANAL_DATASTORE.satni.get_valid_min())
            elif col == 3: #max
                return str(KANAL_DATASTORE.satni.get_valid_max())
            elif col == 4: #obuhvat
                return str(KANAL_DATASTORE.satni.get_valid_obuhvat())
            elif col == 5: #minutni broj OK ispod 0
                return str(KANAL_DATASTORE.koncentracija.get_korekcija_broj_ispod_0())
            else: #broj minutnih korekcija ispod LDL
                return str(KANAL_DATASTORE.koncentracija.get_korekcija_broj_ispod_LDL())
        # BACKGROUND ROLE - boja pozadine ćelije
        if role == QtCore.Qt.BackgroundRole:
            # cilj je obojati pozadinu ćelije u crveno ako je obuhvat los
            obuhvat = KANAL_DATASTORE.satni.get_valid_obuhvat()
            if obuhvat < 75.0 :
                # los obuhvat, vrati transparentnu crvenu boju
                return QtGui.QBrush(QtGui.QColor(255,0,0,80))
        # TOOLTIP ROLE - tooltip na mouseover ćelije
        if role == QtCore.Qt.ToolTipRole:
            if col == 0: #average
                return str(KANAL_DATASTORE.satni.get_valid_average())
            elif col == 1: #std
                return str(KANAL_DATASTORE.satni.get_valid_std())
            elif col == 2: #min
                return str(KANAL_DATASTORE.satni.get_valid_min())
            elif col == 3: #max
                return str(KANAL_DATASTORE.satni.get_valid_max())
            elif col == 4: #obuhvat
                return str(KANAL_DATASTORE.satni.get_valid_obuhvat())
            elif col == 5: #minutni broj OK ispod 0
                return str(KANAL_DATASTORE.koncentracija.get_korekcija_broj_ispod_0())
            else: #broj minutnih korekcija ispod LDL
                return str(KANAL_DATASTORE.koncentracija.get_korekcija_broj_ispod_LDL())

    def headerData(self, section, orientation, role):
        """
        BITNA QT FUNKCIJA. Preko nje view definira nazive redaka i stupaca u tablici.
        """
        #TODO! mjerne jedinice moram negdje slkepati tricky stuff... stvarni nisu nužno npr. ako se ucita CO i O3
        # dohvacanje liste kanala i opisa iz sessiona
        kanali = self.session.sviKanali
        opisMap = self.session.get_mapu_kanala_ID_OPIS()
        jedinicaMap = self.session.get_mapu_kanala_ID_JEDINICA()
        if orientation == QtCore.Qt.Vertical:
            # prikazi opis kanala za redke
            if role == QtCore.Qt.DisplayRole:
                kanal = kanali[section]
                opis = str(opisMap[kanal])
                jedinica = str(jedinicaMap[kanal])
                if jedinica.startswith("pp"):
                    return opis + " [" + jedinica + "V]"
                else:
                    return opis + " [" + jedinica + "]"
        if orientation == QtCore.Qt.Horizontal:
            # prikazi nazive stupaca
            if role == QtCore.Qt.DisplayRole:
                if section == 0:
                    return 'Average'
                elif section == 1:
                    return 'Std'
                elif section == 2:
                    return 'Min'
                elif section == 3:
                    return 'Max'
                elif section == 4:
                    return 'Obuhvat'
                elif section == 5:
                    return 'Broj ispod 0.0'
                else:
                    return 'Broj ispod LDL'

    @property
    def session(self):
        """Getter session objekta sa podacima za sve kanale."""
        return self._SESSION

    @session.setter
    def session(self, x):
        """Setter session objekta sa podacima za sve kanale."""
        self._SESSION = x
        # notifikacija o promjeni podataka za sve view-ove koji su spojeni
        self.layoutChanged.emit()

    def refresh(self):
        """Funkcija koja poziva na refresh tablice."""
        # notifikacija o promjeni podataka za sve view-ove koji su spojeni
        self.layoutChanged.emit()
