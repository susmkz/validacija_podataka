#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import numpy as np
import pandas as pd
from PyQt5 import QtCore


class KorekcijaTablica(QtCore.QAbstractTableModel):
    """
    Klasa za korekcijske parametre (A, B, Sr)
    """
    # DEFINIRANJE POSEBNOG SIGNALA - update persistant delegata za racunanje AB i brisanje redka
    update_persistent_delegates_korekcija = QtCore.pyqtSignal()

    def __init__(self):
        """
        Konstruktor klase
        """
        super(KorekcijaTablica, self).__init__()
        # stupci koji moraju postojati u frejmu, dodatno frejm mora imati vremenski indeks
        self._EXPECTED_COLUMNS = ['vrijeme', 'A', 'B', 'Sr']
        # definiramo dummy red za insert operacije
        self._dummydata = {'vrijeme': '', 'A': np.NaN, 'B': np.NaN, 'Sr': np.NaN}
        # pandas DataFrame sa podacima (sa zadanim stupcima)
        self._DF = pd.DataFrame(columns=self._EXPECTED_COLUMNS)
        # dodavanje datafrejma automatski dodaje prazan red za insert
        self.dataframe = pd.DataFrame(columns=self._EXPECTED_COLUMNS)
        # kanal Id - ID programa mjerenja iz baze
        self._kanalId = None
        # mapa sa metapodacima kanala (formula, postaja, mjerna jedinica...)
        self._metaData = {}

    def rowCount(self, parent=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Preko nje view dohvaća broj redova u tablici. Broj redova
        odgovara broju redova u frejmu sa podacima
        """
        return len(self._DF)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Preko nje view dohvaća broj stupaca u tablici.
        Prikazujemo 6 stupca:
            stupac 0 --> vrijeme (vrijeme korekcije)
            stupac 1 --> A (nagib pravca)
            stupac 2 --> B (odsjecak na osi y)
            stupac 3 --> Sr (parametar za racunanje LDL)
            stupac 4 --> makni red
            stupac 5 --> racunaj AB iz zero i span podataka
        """
        return 6

    def flags(self, index):
        """
        BITNA QT FUNKCIJA. Preko nje view definira dozvoljene akcije pojedine
        "ćelije" u tablici. Bitno je napomenuti da je svaki element tablice
        EDITABLE.
        """
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

    def data(self, index, role):
        """
        BITNA QT FUNKCIJA. Preko nje view definira što i kako prikazati za pojedinu
        "ćeliju" u tablici. Određujemo prikaz vrijednosti i stila.
        """
        # ako je indeks pogrešno zadan nemamo što raditi
        if not index.isValid():
            return None
        # dohvaćamo red i stupac indeksa
        row = index.row()
        col = index.column()
        # DISPLAY ROLE - sto prikazujemo u ćeliji
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            # stupac 0 je vrijeme, formatiramo ga na human readable nacin
            if col == 0:
                val = self._DF.iloc[row, col]
                if isinstance(val, pd.Timestamp):
                    return str(val.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    return str(val)
            # stupac 4 ne postoji u self._DF, placeholder za "Remove"
            elif col == 4:
                return "Remove"
            # stupac 5 ne postoji u self._DF, placeholder za "Calculate"
            elif col == 5:
                return "Calculate"
            # ostali stupci su poravnati sa tablicom
            else:
                val = self._DF.iloc[row, col]
                return str(val)

    def headerData(self, section, orientation, role):
        """
        BITNA QT FUNKCIJA. Preko nje view definira nazive redaka i stupaca u tablici.
        """
        if orientation == QtCore.Qt.Vertical:
            # naziv redka je njegov redni broj
            if role == QtCore.Qt.DisplayRole:
                return str(section)
        if orientation == QtCore.Qt.Horizontal:
            # naziv stupca odgovara onome u tablici uz iznimku stupca 4 i 5
            if role == QtCore.Qt.DisplayRole:
                # stupac 4 ne postoji u self._DF, moramo vratiti odgovarajuci opis
                if section == 4:
                    return "Remove"
                # stupac 5 ne postoji u self._DF, moramo vratiti odgovarajuci opis
                elif section == 5:
                    return "Calculate"
                # svi ostali stupci su u dobrom redosljedu sa frejmom self._DF
                elif section in [2,3]:
                    if self.jedinica.startswith('pp'):
                        return str(self._DF.columns[section]) + " [" + str(self.jedinica) + "V]"
                    else:
                        return str(self._DF.columns[section]) + " [" + str(self.jedinica) + "]"
                else:
                    return str(self._DF.columns[section])

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """
        BITNA QT FUNKCIJA. Funkcija definira kako se spremanju editirane vrijednosti
        (value) u zadani indeks (index). Funkcija vraća True ako je operacija uspješna,
        False inače.
        """
        # ako je indeks pogrešno zadan nemamo što raditi
        if not index.isValid():
            return False
        red = index.row()
        stupac = index.column()
        # dohvaćamo red i stupac indeksa
        try:
            if stupac == 0:
                # za 0 stupac ('vrijeme') moramo propaziti na format
                if value == "":
                    # prazan stupac (vrijeme nije zadano)
                    return False
                # pretvorimo vrijeme u pandas timestamp
                ts = pd.to_datetime(value)
                # upisivanje vremena u zadani stupac i red
                self._DF.iloc[red, stupac] = ts
                # sort index
                self._DF.sort_index(inplace=True)
                # napravi novi redak ako se editira zadnji redak u tablici
                # to je mehanizam na koji tablica raste (dodavanjem vremena u zadnji element)
                if red == self.rowCount() - 1:
                    self.insertRows(123123)  # dummy positional argument
            elif stupac in [1, 2, 3]:
                # pretvaramo vrijednost u float za A, B, Sr
                self._DF.iloc[red, stupac] = float(value)
            else:
                # stupci 4 i 5 su placeholderi, ignoriamo promjenu na njima
                pass
            # notifikacija da je došlo do promjene u tablici
            self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
            # ako je doslo do promjene u stupcu 'vrijeme' (stupac 0) sortiramo po vremenu
            if stupac == 0:
                self.sort(0, QtCore.Qt.AscendingOrder)
            # vrati True, kao signal da je promjena uspješno napravljena
            return True
        except Exception as err:
            # log pogreške
            logging.error(str(err), exc_info=True)
            # vrati False, kao signal da promjena nije napravljena
            return False

    def sort(self, col, order):
        """
        Funkcija sortira tablicu prema broju stupca i redosljedu (QtCore.Qt.AscendingOrder
        ili QtCore.Qt.DescendingOrder).

        Dozvoljeno je samo sortiranje 0 stupca (vrijeme) i samo u uzlaznom
        nacinu. Cilj je da vremena uvijek idu od najmanjeg do najvećeg bez obzira
        kojim redosljedom se dodaju u tablicu.
        """
        if col == 0 and order == QtCore.Qt.AscendingOrder:
            # bitno najaviti promjenu redosljeda redaka
            self.layoutAboutToBeChanged.emit()
            self._DF.iloc[-1, 0] = pd.NaT # zadnji redak tablice je u biti prazan, vrijeme je NaT (Not a Time)
            self._DF = self._DF.sort_values('vrijeme') # sortiranje
            self._DF.iloc[-1, 0] = '' # prebacujemo zadnji vremenski indeks nazad u prazan string
            self.layoutChanged.emit() # notifikacija o promjeni redosljeda redaka
            # moramo emitirati posebni signal koji javlja delegatima u
            #tablici (gumbima za brisanje i racunanje AB) da se ponovno povežu sa
            #odgovarajućim redcima (želimo izbjeći da red 2 brise red 4 isl...)
            self.update_persistent_delegates_korekcija.emit()
        else:
            pass

    def insertRows(self, position, rows=1, index=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Mehanizam za dodavanje redova u tablicu. Vrati True ako
        je red uspješno dodan, False inače.
        """
        try:
            # bitno je pozvati beginInsertRows - dodajemo na kraj tablice (iza zadnjeg reda)
            self.beginInsertRows(QtCore.QModelIndex(),
                                 position,
                                 position + rows - 1)
            # stvaramo dodatni red (koristimo _dummydata)
            red = pd.DataFrame(data=self._dummydata,
                               columns=self._EXPECTED_COLUMNS,
                               index=[len(self._DF)])
            self._DF = self._DF.append(red) # upisivanje na kraj datafrejma
            self._DF = self._DF.reindex() # reindeksiranje
            self.endInsertRows() # bitno je pozvati endInsertRows kao signal kraja dodavanja
            self.layoutChanged.emit() # notifikacija o promjeni tablice
            self.sort(0, QtCore.Qt.AscendingOrder) # sortiramo da sačuvamo vremenski redosljed
            # return True kao signal uspješnosti radnje
            return True
        except Exception as err:
            # log pogreške
            logging.error(str(err), exc_info=True)
            # return False kao signal neuspjeha radnje
            return False

    def removeRows(self, position, rows=1, index=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Mehanizam za brisanje redova iz tablicu. Vrati True ako
        je red uspješno izbrisan, False inače.
        """
        try:
            if position == self.rowCount() - 1:
                # nemoj maknuti zadnji red tablice NIKADA!
                # umjesto brisanja reda , samo izbrisi sve vrijednosti u tablici
                for col in range(1,len(self._DF.columns)):
                    self._DF.iloc[-1, col] = np.NaN
                self.layoutChanged.emit() #notifikacija o promjeni tablice
                return False  # return False kao signal neuspjeha brisanja reda
            # bilo koji red (osim zadnjeg!)
            # bitno je pozvati beginRemoveRows - signal pocetka brisanja
            self.beginRemoveRows(QtCore.QModelIndex(),
                                 position,
                                 position + rows - 1)
            self._DF.drop(self._DF.index[position], inplace=True) # brisemo red iz tablice
            self._DF = self._DF.reindex() # reindeks tablice
            self.endRemoveRows() # bitno je pozvati endRemoveRows - singnal kraja brisanja
            self.layoutChanged.emit() # notifikacija o promjeni tablice
            self.sort(0, QtCore.Qt.AscendingOrder) # sortiramo da sačuvamo vremenski redosljed
            # return True kao signal uspješnosti brisanja reda
            return True
        except Exception as err:
            # log pogreške
            logging.error(str(err), exc_info=True)
            # return False kao signal neuspjeha radnje
            return False  # return False kao signal neuspjeha brisanja reda

    @property
    def dataframe(self):
        """
        Getter datafrejma sa podacima (kopije).

        self._DF ima dummy red na kraju za unos novih podataka, potrebno je vratiti
        samo osnovni frejm bez zadnjeg reda. Zbog nacina unosa zadnji red je uvijek dummy.

        Novi red se stvara samo prilikom promjene vremena u tablici, tada se sortira tako
        da novi prazni red uvijek bude zadnji. Slicno i za brisanje podataka. Sort osigurava
        da je dummy zadnji red.
        """
        # o duljini frejma, 0 je nemomoguće jer uvijek postoji dummy red, 1 je moguć
        # i ako je to slucaj imamo samo dummy red. Bilo sto veće od 2 je legitimno za rad.
        if len(self._DF) >= 2:
            # vrati datafrejm bez zadnjeg reda
            out = self._DF.iloc[:-1,:]
            return out.copy()
        else:
            # ako imamp praznu tablicu, slajs svega osim zadnjeg reda je besmislen,
            # vrati dobro formatirani prazni datafrejm.
            return pd.DataFrame(columns=self._EXPECTED_COLUMNS)

    @dataframe.setter
    def dataframe(self, x):
        """
        Setter datafrejma sa podacima.

        Prilikom dodavanja frejma u model, moramo paziti da dodamo prazan red na kraj
        datafrejma.
        """
        # provjeri da li je ulaz DataFrame objekt
        if isinstance(x, pd.core.frame.DataFrame):
            if len(x) == 0:
                # ako je ulazni dataframe prazan, napravi novi sa dobro poslaganim stupcima
                self._DF = pd.DataFrame(columns=self._EXPECTED_COLUMNS)
            else:
                # preslozi stupce o odgovarajući redosljed
                self._DF = x[self._EXPECTED_COLUMNS]
            #XXX! force type change to np.float - problem sa učitavanjem spremljenih sessiona
            self._DF = self._DF.astype({"A":np.float64, "B":np.float64, 'Sr':np.float64})
            # dodaj prazan red na kraj
            red = pd.DataFrame(data=self._dummydata,
                               columns=self._EXPECTED_COLUMNS,
                               index=[len(self._DF)])
            self._DF = self._DF.append(red)
            # sort tablice
            self.sort(0, QtCore.Qt.AscendingOrder)
            # reindex tablice
            self._DF.reset_index()
            # signaliziraj da je došlo do promjene u tablici
            self.layoutChanged.emit()
        else:
            raise TypeError('Not a pandas DataFrame object'.format(type(x)))

    @property
    def kanalId(self):
        """Getter ID programa mjerenja (jedinstvena oznaka u bazi)."""
        return self._kanalId

    @kanalId.setter
    def kanalId(self, x):
        """Setter ID programa mjerenja (jedinstvena oznaka u bazi)."""
        self._kanalId = x

    @property
    def metaData(self):
        """Getter mape metapodataka o kanalu (postaja, formula, jedinica ...)."""
        return self._metaData

    @metaData.setter
    def metaData(self, mapa):
        """Setter mape metapodataka o kanalu (postaja, formula, jedinica ...)."""
        self._metaData = mapa

    @property
    def unitConversionFactor(self):
        """
        Getter konverzijskog volumena za pretvorbu ppb - ug/m3 (float).
        ppb vrijednost * faktor = ug/m3
        ug/m3 * 1/faktor = ppb
        Default je 1.0 (neutralni element za množenje)
        """
        return self._metaData.get('konvVUM', 1.0)

    @property
    def postaja(self):
        """Getter naziva postaje iz metapodataka."""
        x = self._metaData.get('postajaNaziv', '???')
        return x

    @property
    def formula(self):
        """Getter formule iz metapodataka."""
        x = self._metaData.get('komponentaFormula', '???')
        return x

    @property
    def jedinica(self):
        """Getter mjerne jedinice iz metapodataka."""
        x = self._metaData.get('komponentaMjernaJedinica', '???')
        return x

    @jedinica.setter
    def jedinica(self, x):
        """Setter mjerne jedinice u metapodatake."""
        self._metaData['komponentaMjernaJedinica'] = str(x)

    @property
    def puniOpis(self):
        """Getter punog opisa iz metapodataka (postaja : formula mjerna_jedinica)."""
        return "{0} : {1} {2}".format(self.postaja, self.formula, self.jedinica)

    @property
    def opis(self):
        """Getter kratkog opisa iz metapodataka (postaja : formula)."""
        return "{0} : {1}".format(self.postaja, self.formula)

    @property
    def povezaniKanali(self):
        """Getter liste povezanih kanala tj. liste njihovih ID programa mjerenja iz baze
        (NOx ili PM grupa)."""
        x = self._metaData['povezaniKanali']
        return x

    @property
    def isNOx(self):
        """ True ako je formula metapodataka u NOx grupi. """
        return self.formula in ['NOx', 'NO', 'NO2']

    @property
    def isPM(self):
        """ True ako je formula metapodataka u PM grupi. """
        return self.formula in ['PM10', 'PM1', 'PM2.5']

    def convert_units(self, ppx=True):
        """
        Funkcija pretvara vrijednosti u drugi sustav ovisno o parametru "ppx".
        Ako je "ppx" True, pretvaram u ppb ili ppm. Ako je "ppx" False, pretvaram
        u ug/m3 ili mg/m3. Model zna u kojim je mjernim jedinicama (metapodaci)
        te nakon promjene mora promjeniti metapodatke da reflektira promjenu.

        P.S. mjenjamo samo 'B'. 'A' je nagib pravca tj. ne skalira se.
        
        ispravak...
        promjenu metapodataka o jedinici ostavljamo funkciji koja zove ovu funkciju
        """
        for col in ['B', 'Sr']:
            if ppx and (self.jedinica not in ['ppb', 'ppm']):
                # PRETVARANJE U PPx (PPB ili PPM)
                currentVals = self._DF.loc[:,col].values
                # primjeni konverziju u ppm ili ppb
                newVals = currentVals / self.unitConversionFactor
                # postavi nove vrijednosti
                self._DF.loc[:,col] = newVals
            elif (not ppx) and (self.jedinica not in ['ug/m3', 'mg/m3']):
                # PRETVARANJE U ug/m3 ili mg/m3
                currentVals = self._DF.loc[:,col].values
                # primjeni konverziju u ug/m3 ili mg/m3
                newVals = currentVals * self.unitConversionFactor
                # postavi nove vrijednosti
                self._DF.loc[:,col] = newVals
            else:
                # nema potrebe za konverzijom (vec smo u dobrom sustavu)
                pass
        # singnal da je došlo do promjene u tablici
        self.layoutChanged.emit()
        # moramo emitirati posebni signal koji javlja delegatima u
        #tablici (gumbima za brisanje i racunanje AB) da se ponovno povežu sa
        #odgovarajućim redcima (želimo izbjeći da red 2 brise red 4 isl...)
        self.update_persistent_delegates_korekcija.emit()


    def set_AB_for_row(self, red, a, b):
        """
        Pomoćna funkcija koja reagira na Poziv za racunanje AB iz tablice.
        Postavljaju se vrijednosti A i B za neki red.
        """
        # postavljanje vrijednosti
        self._DF.iloc[red, 1] = a
        self._DF.iloc[red, 2] = b
        # singnal da je došlo do promjene u tablici
        self.layoutChanged.emit()
        # moramo emitirati posebni signal koji javlja delegatima u
        #tablici (gumbima za brisanje i racunanje AB) da se ponovno povežu sa
        #odgovarajućim redcima (želimo izbjeći da red 2 brise red 4 isl...)
        self.update_persistent_delegates_korekcija.emit()

    def get_pickle_map(self):
        """
        Funkcija za pomoć prilikom SAVE - LOAD operacija. Sprema sve bitne varijable
        u mapu.
        """
        mapa = {}
        mapa['dataframe'] = self.dataframe
        mapa['kanalId'] = self.kanalId
        mapa['metaData'] = self.metaData
        return mapa

    def set_pickle_map(self, mapa):
        """
        Funkcija za pomoć prilikom SAVE - LOAD operacija. Iz mape preuzima vrijednosti
        koje postavlja u zadane varijable.
        """
        self.kanalId = mapa['kanalId']
        self.metaData = mapa['metaData']
        self.dataframe = mapa['dataframe']


class KorekcijaTablicaNO2(QtCore.QAbstractTableModel):
    """
    Klasa za korekcijske parametar Ec (efikasnost konvertera)
    """
    # DEFINIRANJE POSEBNOG SIGNALA - update persistant delegata za brisanje redka
    update_persistent_delegates_korekcija = QtCore.pyqtSignal()

    def __init__(self):
        """
        Konstruktor klase
        """
        super(KorekcijaTablicaNO2, self).__init__()
        # stupci koji moraju postojati u frejmu, dodatno frejm mora imati vremenski indeks
        self._EXPECTED_COLUMNS = ['vrijeme', 'Ec']
        # definiramo dummy red za insert operacije
        self._dummydata = {'vrijeme': '', 'Ec': np.NaN}
        # pandas DataFrame sa podacima (sa zadanim stupcima)
        self._DF = pd.DataFrame(columns=self._EXPECTED_COLUMNS)
        # dodavanje datafrejma automatski dodaje prazan red za insert
        self.dataframe = pd.DataFrame(columns=self._EXPECTED_COLUMNS)
        # kanal Id - ID programa mjerenja iz baze
        self._kanalId = None
        # mapa sa metapodacima kanala (formula, postaja, mjerna jedinica...)
        self._metaData = {}

    def rowCount(self, parent=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Preko nje view dohvaća broj redova u tablici. Broj redova
        odgovara broju redova u frejmu sa podacima
        """
        return len(self._DF)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Preko nje view dohvaća broj stupaca u tablici.
            stupac 0 --> vrijeme (vrijeme korekcije)
            stupac 1 --> Ec (efikasnost konverera)
            stupac 2 --> makni red
        """
        return 3

    def flags(self, index):
        """
        BITNA QT FUNKCIJA. Preko nje view definira dozvoljene akcije pojedine
        "ćelije" u tablici. Bitno je napomenuti da je svaki element tablice
        EDITABLE.
        """
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

    def data(self, index, role):
        """
        BITNA QT FUNKCIJA. Preko nje view definira što i kako prikazati za pojedinu
        "ćeliju" u tablici. Određujemo prikaz vrijednosti i stila.
        """
        # ako je indeks pogrešno zadan nemamo što raditi
        if not index.isValid():
            return None
        # dohvaćamo red i stupac indeksa
        row = index.row()
        col = index.column()
        # DISPLAY ROLE - sto prikazujemo u ćeliji
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            # stupac 0 je vrijeme, formatiramo ga na human readable nacin
            if col == 0:
                val = self._DF.iloc[row, col]
                if isinstance(val, pd.Timestamp):
                    return str(val.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    return str(val)
            # stupac za efikasnost konvertera
            elif col == 1:
                val = self._DF.iloc[row, col]
                return str(val)
            # stupac 2 ne postoji u self._DF, placeholder za "Remove"
            else:
                return "Remove"

    def headerData(self, section, orientation, role):
        """
        BITNA QT FUNKCIJA. Preko nje view definira nazive redaka i stupaca u tablici.
        """
        if orientation == QtCore.Qt.Vertical:
            # naziv redka je njegov redni broj
            if role == QtCore.Qt.DisplayRole:
                return str(section)
        if orientation == QtCore.Qt.Horizontal:
            # naziv stupca odgovara onome u tablici uz iznimku stupca 4 i 5
            if role == QtCore.Qt.DisplayRole:
                # stupac 2 ne postoji u self._DF, moramo vratiti odgovarajuci opis
                if section == 2:
                    return "Remove"
                # svi ostali stupci su u dobrom redosljedu sa frejmom self._DF
                else:
                    return str(self._DF.columns[section])

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """
        BITNA QT FUNKCIJA. Funkcija definira kako se spremanju editirane vrijednosti
        (value) u zadani indeks (index). Funkcija vraća True ako je operacija uspješna,
        False inače.
        """
        # ako je indeks pogrešno zadan nemamo što raditi
        if not index.isValid():
            return False
        red = index.row()
        stupac = index.column()
        # dohvaćamo red i stupac indeksa
        try:
            if stupac == 0:
                # za 0 stupac ('vrijeme') moramo propaziti na format
                if value == "":
                    # prazan stupac (vrijeme nije zadano)
                    return False
                # pretvorimo vrijeme u pandas timestamp
                ts = pd.to_datetime(value)
                # upisivanje vremena u zadani stupac i red
                self._DF.iloc[red, stupac] = ts
                # sort index
                self._DF.sort_index(inplace=True)
                # napravi novi redak ako se editira zadnji redak u tablici
                # to je mehanizam na koji tablica raste (dodavanjem vremena u zadnji element)
                if red == self.rowCount() - 1:
                    self.insertRows(123123)  # dummy positional argument
            elif stupac == 1:
                # pretvaramo vrijednost u float za Ec
                self._DF.iloc[red, stupac] = float(value)
            else:
                # stupac 2 je placeholder za gumb, ignoriamo promjenu
                pass
            # notifikacija da je došlo do promjene u tablici
            self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
            # ako je doslo do promjene u stupcu 'vrijeme' (stupac 0) sortiramo po vremenu
            if stupac == 0:
                self.sort(0, QtCore.Qt.AscendingOrder)
            # vrati True, kao signal da je promjena uspješno napravljena
            return True
        except Exception as err:
            # log pogreške
            logging.error(str(err), exc_info=True)
            # vrati False, kao signal da promjena nije napravljena
            return False

    def sort(self, col, order):
        """
        Funkcija sortira tablicu prema broju stupca i redosljedu (QtCore.Qt.AscendingOrder
        ili QtCore.Qt.DescendingOrder).

        Dozvoljeno je samo sortiranje 0 stupca (vrijeme) i samo u uzlaznom
        nacinu. Cilj je da vremena uvijek idu od najmanjeg do najvećeg bez obzira
        kojim redosljedom se dodaju u tablicu.
        """
        if col == 0 and order == QtCore.Qt.AscendingOrder:
            # bitno najaviti promjenu redosljeda redaka
            self.layoutAboutToBeChanged.emit()
            self._DF.iloc[-1, 0] = pd.NaT # zadnji redak tablice je u biti prazan, vrijeme je NaT (Not a Time)
            self._DF = self._DF.sort_values('vrijeme') # sortiranje
            self._DF.iloc[-1, 0] = '' # prebacujemo zadnji vremenski indeks nazad u prazan string
            self.layoutChanged.emit() # notifikacija o promjeni redosljeda redaka
            # moramo emitirati posebni signal koji javlja delegatima u
            #tablici da se ponovno povežu sa odgovarajućim redcima
            self.update_persistent_delegates_korekcija.emit()
        else:
            pass

    def insertRows(self, position, rows=1, index=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Mehanizam za dodavanje redova u tablicu. Vrati True ako
        je red uspješno dodan, False inače.
        """
        try:
            # bitno je pozvati beginInsertRows - dodajemo na kraj tablice (iza zadnjeg reda)
            self.beginInsertRows(QtCore.QModelIndex(),
                                 position,
                                 position + rows - 1)
            # stvaramo dodatni red (koristimo _dummydata)
            red = pd.DataFrame(data=self._dummydata,
                               columns=self._EXPECTED_COLUMNS,
                               index=[len(self._DF)])
            self._DF = self._DF.append(red) # upisivanje na kraj datafrejma
            self._DF = self._DF.reindex() # reindeksiranje
            self.endInsertRows() # bitno je pozvati endInsertRows kao signal kraja dodavanja
            self.layoutChanged.emit() # notifikacija o promjeni tablice
            self.sort(0, QtCore.Qt.AscendingOrder) # sortiramo da sačuvamo vremenski redosljed
            # return True kao signal uspješnosti radnje
            return True
        except Exception as err:
            # log pogreške
            logging.error(str(err), exc_info=True)
            # return False kao signal neuspjeha radnje
            return False

    def removeRows(self, position, rows=1, index=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Mehanizam za brisanje redova iz tablicu. Vrati True ako
        je red uspješno izbrisan, False inače.
        """
        try:
            if position == self.rowCount() - 1:
                # nemoj maknuti zadnji red tablice NIKADA!
                # umjesto brisanja reda , samo izbrisi sve vrijednosti u tablici
                for col in range(1,len(self._DF.columns)):
                    self._DF.iloc[-1, col] = np.NaN
                self.layoutChanged.emit() #notifikacija o promjeni tablice
                return False  # return False kao signal neuspjeha brisanja reda
            # bilo koji red (osim zadnjeg!)
            # bitno je pozvati beginRemoveRows - signal pocetka brisanja
            self.beginRemoveRows(QtCore.QModelIndex(),
                                 position,
                                 position + rows - 1)
            self._DF.drop(self._DF.index[position], inplace=True) # brisemo red iz tablice
            self._DF = self._DF.reindex() # reindeks tablice
            self.endRemoveRows() # bitno je pozvati endRemoveRows - singnal kraja brisanja
            self.layoutChanged.emit() # notifikacija o promjeni tablice
            self.sort(0, QtCore.Qt.AscendingOrder) # sortiramo da sačuvamo vremenski redosljed
            # return True kao signal uspješnosti brisanja reda
            return True
        except Exception as err:
            # log pogreške
            logging.error(str(err), exc_info=True)
            # return False kao signal neuspjeha radnje
            return False  # return False kao signal neuspjeha brisanja reda

    @property
    def dataframe(self):
        """
        Getter datafrejma sa podacima (kopije).

        self._DF ima dummy red na kraju za unos novih podataka, potrebno je vratiti
        samo osnovni frejm bez zadnjeg reda. Zbog nacina unosa zadnji red je uvijek dummy.

        Novi red se stvara samo prilikom promjene vremena u tablici, tada se sortira tako
        da novi prazni red uvijek bude zadnji. Slicno i za brisanje podataka. Sort osigurava
        da je dummy zadnji red.
        """
        # o duljini frejma, 0 je nemomoguće jer uvijek postoji dummy red, 1 je moguć
        # i ako je to slucaj imamo samo dummy red. Bilo sto veće od 2 je legitimno za rad.
        if len(self._DF) >= 2:
            # vrati datafrejm bez zadnjeg reda
            out = self._DF.iloc[:-1,:]
            return out.copy()
        else:
            # ako imamp praznu tablicu, slajs svega osim zadnjeg reda je besmislen,
            # vrati dobro formatirani prazni datafrejm.
            return pd.DataFrame(columns=self._EXPECTED_COLUMNS)

    @dataframe.setter
    def dataframe(self, x):
        """
        Setter datafrejma sa podacima.

        Prilikom dodavanja frejma u model, moramo paziti da dodamo prazan red na kraj
        datafrejma.
        """
        # provjeri da li je ulaz DataFrame objekt
        if isinstance(x, pd.core.frame.DataFrame):
            if len(x) == 0:
                # ako je ulazni dataframe prazan, napravi novi sa dobro poslaganim stupcima
                self._DF = pd.DataFrame(columns=self._EXPECTED_COLUMNS)
            else:
                # preslozi stupce o odgovarajući redosljed
                self._DF = x[self._EXPECTED_COLUMNS]
            # dodaj prazan red na kraj
            red = pd.DataFrame(data=self._dummydata,
                               columns=self._EXPECTED_COLUMNS,
                               index=[len(self._DF)])
            self._DF = self._DF.append(red)
            # sort tablice
            self.sort(0, QtCore.Qt.AscendingOrder)
            # reindex tablice
            self._DF.reset_index()
            # signaliziraj da je došlo do promjene u tablici
            self.layoutChanged.emit()
        else:
            raise TypeError('Not a pandas DataFrame object'.format(type(x)))

    @property
    def kanalId(self):
        """Getter ID programa mjerenja (jedinstvena oznaka u bazi)."""
        return self._kanalId

    @kanalId.setter
    def kanalId(self, x):
        """Setter ID programa mjerenja (jedinstvena oznaka u bazi)."""
        self._kanalId = x

    @property
    def metaData(self):
        """Getter mape metapodataka o kanalu (postaja, formula, jedinica ...)."""
        return self._metaData

    @metaData.setter
    def metaData(self, mapa):
        """Setter mape metapodataka o kanalu (postaja, formula, jedinica ...)."""
        self._metaData = mapa

    @property
    def unitConversionFactor(self):
        """
        Getter konverzijskog volumena za pretvorbu ppb - ug/m3 (float).
        ppb vrijednost * faktor = ug/m3
        ug/m3 * 1/faktor = ppb
        Default je 1.0 (neutralni element za množenje)
        """
        return self._metaData.get('konvVUM', 1) # Ec je postotak, nema konverzije

    @property
    def postaja(self):
        """Getter naziva postaje iz metapodataka."""
        x = self._metaData.get('postajaNaziv', '???')
        return x

    @property
    def formula(self):
        """Getter formule iz metapodataka."""
        x = self._metaData.get('komponentaFormula', '???')
        return x

    @property
    def jedinica(self):
        """Getter mjerne jedinice iz metapodataka."""
        x = self._metaData.get('komponentaMjernaJedinica', '???')
        return x

    @jedinica.setter
    def jedinica(self, x):
        """Setter mjerne jedinice u metapodatake."""
        self._metaData['komponentaMjernaJedinica'] = str(x)

    @property
    def puniOpis(self):
        """Getter punog opisa iz metapodataka (postaja : formula mjerna_jedinica)."""
        return "{0} : {1} {2}".format(self.postaja, self.formula, self.jedinica)

    @property
    def opis(self):
        """Getter kratkog opisa iz metapodataka (postaja : formula)."""
        return "{0} : {1}".format(self.postaja, self.formula)

    @property
    def povezaniKanali(self):
        """Getter liste povezanih kanala tj. liste njihovih ID programa mjerenja iz baze
        (NOx ili PM grupa)."""
        x = self._metaData['povezaniKanali']
        return x

    @property
    def isNOx(self):
        """ True ako je formula metapodataka u NOx grupi. """
        return self.formula in ['NOx', 'NO', 'NO2']

    @property
    def isPM(self):
        """ True ako je formula metapodataka u PM grupi. """
        return self.formula in ['PM10', 'PM1', 'PM2.5']

    def convert_units(self, ppx=True):
        """
        Funkcija pretvara vrijednosti u drugi sustav ovisno o parametru "ppx".
        Ako je "ppx" True, pretvaram u ppb ili ppm. Ako je "ppx" False, pretvaram
        u ug/m3 ili mg/m3. Model zna u kojim je mjernim jedinicama (metapodaci)
        te nakon promjene mora promjeniti metapodatke da reflektira promjenu.

        Funkcija je u biti nepotrebna. Ec je bezdimenzionalna veličina u postocima.
        Nema konverziju u i iz ppb-a - samo moramo prebaciti jedinicu
        
        ispravak...
        promjenu metapodataka o jedinici ostavljamo funkciji koja zove ovu funkciju
        """
        pass
#        if ppx and (self.jedinica not in ['ppb', 'ppm']):
#            # PRETVARANJE U PPx (PPB ili PPM)
#            # postavi nove jedinice u metapodatke
#            if self.jedinica == 'ug/m3':
#                self.jedinica = 'ppb'
#            else:
#                self.jedinica = 'ppm'
#        elif (not ppx) and (self.jedinica not in ['ug/m3', 'mg/m3']):
#            # PRETVARANJE U ug/m3 ili mg/m3
#            # postavi nove jedinice u metapodatke
#            if self.jedinica == 'ppb':
#                self.jedinica = 'ug/m3'
#            else:
#                self.jedinica = 'mg/m3'
#        else:
#            # nema potrebe za konverzijom (vec smo u dobrom sustavu)
#            pass
        # singnal da je došlo do promjene u tablici
        self.layoutChanged.emit()
        # moramo emitirati posebni signal koji javlja delegatima u
        #tablici (gumbima za brisanje i racunanje AB) da se ponovno povežu sa
        #odgovarajućim redcima (želimo izbjeći da red 2 brise red 4 isl...)
        self.update_persistent_delegates_korekcija.emit()

    def get_pickle_map(self):
        """
        Funkcija za pomoć prilikom SAVE - LOAD operacija. Sprema sve bitne varijable
        u mapu.
        """
        mapa = {}
        mapa['dataframe'] = self.dataframe
        mapa['kanalId'] = self.kanalId
        mapa['metaData'] = self.metaData
        return mapa

    def set_pickle_map(self, mapa):
        """
        Funkcija za pomoć prilikom SAVE - LOAD operacija. Iz mape preuzima vrijednosti
        koje postavlja u zadane varijable.
        """
        self.kanalId = mapa['kanalId']
        self.metaData = mapa['metaData']
        self.dataframe = mapa['dataframe']
