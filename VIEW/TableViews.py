#!/usr/bin/python3
# -*- coding: utf-8 -*-
import pandas as pd
import datetime
from PyQt5 import QtCore, QtGui, QtWidgets


class ConcentrationsTableView(QtWidgets.QTableView):
    """
    Klasa za tablični prikaz koncentracije (view).
    Definiramo signal koji tablica koristi za indikaciju promjene flaga,
    kontekstni meni za promjenu flaga i način kako se biraju elementi u tablici.
    """
    #DEFINICIJA SIGNALA ZA PROMJENU FLAGA -> kanal, str->vrijeme u ISO formatu, bool->OK ili BAD
    signal_flag_change = QtCore.pyqtSignal(int, str, str, bool)

    def __init__(self, parent=None):
        """Konstruktor klase."""
        super(ConcentrationsTableView, self).__init__(parent=parent)
        # select pojedinih redova
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # dozvoljavamo selekciju od-do (kontinuiranu)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ContiguousSelection)

    def contextMenuEvent(self, event):
        """
        Reimplementacija kontekstnog menija. Definiramo mehanizam za promjenu flaga.
        """
        # definiramo menu
        menu = QtWidgets.QMenu(self)
        # definiramo akcije
        changeFlagOK = menu.addAction("Promjeni u dobar flag")
        changeFlagBAD = menu.addAction("Promjeni u los flag")
        # poziv koji prikazuje menu na ekranu
        action = menu.exec_(QtGui.QCursor().pos())
        # lokacija vremena od/do
        indeksi = self.selectedIndexes() # lista svih izabranih indeksa
        redovi = [i.row() for i in indeksi] # zanimaju nas redovi (a ne QModelIndex instance)
        kanal = self.model().kanalId # zanima nas koji kanal poteže promjenu flaga
        # adaptacija vremena (dohvaćamo string iz headera stupca)
        vrijemeOd = self.model().headerData(min(redovi), QtCore.Qt.Vertical, QtCore.Qt.DisplayRole)
        vrijemeDo = self.model().headerData(max(redovi), QtCore.Qt.Vertical, QtCore.Qt.DisplayRole)
        # emit naredbe za promjenu flaga
        if action == changeFlagOK:
            self.signal_flag_change.emit(kanal, vrijemeOd, vrijemeDo, True)
        elif action == changeFlagBAD:
            self.signal_flag_change.emit(kanal, vrijemeOd, vrijemeDo, False)
        else:
            #canceled action...
            pass


class StatistikaTableView(QtWidgets.QTableView):
    """
    Klasa za tablični prikaz statističkih parametara (view).
    """
    def __init__(self, parent=None):
        """Konstruktor klase"""
        super(StatistikaTableView, self).__init__(parent=parent)
        # želimo izbor cijelih redova
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)


class ConcentrationsSatniTableView(QtWidgets.QTableView):
    """
    Klasa za tablični prikaz satno agregiranih koncentracija (view).
    Definiramo signal koji tablica koristi za indikaciju promjene flaga,
    kontekstni meni za promjenu flaga i način kako se biraju elementi u tablici.
    """
    #DEFINICIJA SIGNALA ZA PROMJENU FLAGA -> kanal, str->vrijeme u ISO formatu, bool->OK ili BAD
    signal_flag_change = QtCore.pyqtSignal(int, str, str, bool)

    def __init__(self, parent=None):
        """Konstruktor klase"""
        super(ConcentrationsSatniTableView, self).__init__(parent=parent)
        # select pojedinih redova
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # dozvoljavamo selekciju od-do (kontinuiranu)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ContiguousSelection)

    def contextMenuEvent(self, event):
        """
        Reimplementacija kontekstnog menija. Definiramo mehanizam za promjenu flaga.
        """
        # definiramo menu
        menu = QtWidgets.QMenu(self)
        # definiramo akcije
        changeFlagOK = menu.addAction("Promjeni u dobar flag")
        changeFlagBAD = menu.addAction("Promjeni u los flag")
        # poziv koji prikazuje menu na ekranu
        action = menu.exec_(QtGui.QCursor().pos())
        # get vrijeme od/do
        indeksi = self.selectedIndexes()
        redovi = [i.row() for i in indeksi]
        kanal = self.model().kanalId
        # adaptacija vremena (dohvaćamo string iz headera stupca)
        vrijemeOd = self.model().headerData(min(redovi), QtCore.Qt.Vertical, QtCore.Qt.DisplayRole)
        # move pocetak 1 sat unazad (promjena flaga je na minutnim podacima)
        vrijemeOd = str(pd.to_datetime(vrijemeOd) - datetime.timedelta(hours=1))
        vrijemeDo = self.model().headerData(max(redovi), QtCore.Qt.Vertical, QtCore.Qt.DisplayRole)
        # emit naredbe za promjenu flaga
        if action == changeFlagOK:
            self.signal_flag_change.emit(kanal, vrijemeOd, vrijemeDo, True)
        elif action == changeFlagBAD:
            self.signal_flag_change.emit(kanal, vrijemeOd, vrijemeDo, False)
        else:
            #canceled action...
            pass


class CorrectionsTableView(QtWidgets.QTableView):
    """
    Klasa za tablicu korekcijskih parametara (view). Model ove tablice je
    editablian, dodatno ima permanentne delegate u zadnja 2 reda (gumbi)
    """
    def __init__(self, parent=None):
        """Konstruktor klase"""
        super(CorrectionsTableView, self).__init__(parent=parent)
        #expand with delegates and additional functionality...

    def sredi_delegate_za_tablicu(self):
        """
        Funkcija redefinira delegate za stupce u tablici.
        """
        model = self.model() # instanca modela
        # definiramo koji su stupci za koji delegat
        self.setItemDelegateForColumn(4, DeleteGumbDelegate(self))
        self.setItemDelegateForColumn(5, CalcGumbDelegate(self))
        # zatvaramo i otvaramo delegate za svaki red - cilj je dobro povezivanje
        for red in range(0, model.rowCount()):
            self.closePersistentEditor(model.index(red, 4))
            self.closePersistentEditor(model.index(red, 5))
            self.openPersistentEditor(model.index(red, 4))
            self.openPersistentEditor(model.index(red, 5))

class CorrectionsTableViewNO2(QtWidgets.QTableView):
    """
    Klasa za tablicu korekcijskih parametara NO2 (view). Model ove tablice je
    editablian, dodatno ima permanentne delegate u zadnjem redu (gumb za brisanje reda)
    """
    def __init__(self, parent=None):
        """Konstruktor klase"""
        super(CorrectionsTableViewNO2, self).__init__(parent=parent)
        #expand with delegates and additional functionality...

    def sredi_delegate_za_tablicu(self):
        """
        Funkcija redefinira delegate za stupce u tablici.
        """
        model = self.model() # instanca modela
        # definiramo koji su stupci za koji delegat
        self.setItemDelegateForColumn(2, DeleteGumbDelegate(self))
        # zatvaramo i otvaramo delegate za svaki red - cilj je dobro povezivanje
        for red in range(0, model.rowCount()):
            self.closePersistentEditor(model.index(red, 2))
            self.openPersistentEditor(model.index(red, 2))
########### button delegates ###################################################

class DeleteGumbDelegate(QtWidgets.QItemDelegate):
    """Klasa za delete gumb delegat"""
    # primoran overloadati signal commitData zbog:
    # AttributeError: signal was not defined in the first super-class of class
    commitData = QtCore.pyqtSignal(QtWidgets.QWidget)

    def __init__(self, parent):
        """Konstruktor klase"""
        super(DeleteGumbDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        """BITNA QT FUNKCIJA. Definiranje tipa editora. U našem slučaju to je gumb
        kojeg automatski povezujemo sa callback funkcijom"""
        gumb = QtWidgets.QPushButton('X', parent=parent)
        gumb.clicked.connect(self.delete_or_clear_row)
        return gumb

    def setEditorData(self, editor, index):
        """BITNA QT FUNKCIJA. u biti samo mora biti definirana, delegat ne postavlja
        vrijednosti."""
        pass

    def setModelData(self, editor, model, index):
        """BITNA QT FUNKCIJA. u biti samo mora biti definirana, delegat ne postavlja
        vrijednosti."""
        pass

    def delete_or_clear_row(self, ind):
        """
        Ova funkcija definira što radi gumb. Brisanje reda tablice. Clear je u
        slučaju da je to jedini red (automatski sređeno u modelu).
        """
        # moramo pronaći view u kojem je embedan delegat.
        # sender je gumb, parent je "okvir/layout" u kojem se nalazi gumb, parent toga je tablica.
        # malo nespretno, ali radi
        view = self.sender().parent().parent()
        # kada imam view (tablicu), mogu pronaci model te tablice
        model = view.model()
        # i poziciju delegata u tablici
        indeks = view.indexAt(self.sender().pos())
        # kada znam red, na modelu je da ga makne
        model.removeRows(indeks.row())
        # commitData je bitan jer signalizira promjenu tj. update tablice (view-a)
        self.commitData.emit(self.sender())


class CalcGumbDelegate(QtWidgets.QItemDelegate):
    """Klasa za gumb delegat koji računa nagib A, B iz podataka za zero i span"""
    # primoran overloadati signal commitData zbog:
    # AttributeError: signal was not defined in the first super-class of class
    commitData = QtCore.pyqtSignal(QtWidgets.QWidget)

    def __init__(self, parent):
        """Konstruktor klase"""
        super(CalcGumbDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        """BITNA QT FUNKCIJA. Definiranje tipa editora. U našem slučaju to je gumb
        kojeg automatski povezujemo sa callback funkcijom"""
        gumb = QtWidgets.QPushButton('AB', parent=parent)
        gumb.clicked.connect(self.calculate_AB_for_row)
        return gumb

    def setEditorData(self, editor, index):
        """BITNA QT FUNKCIJA. u biti samo mora biti definirana, delegat ne postavlja
        vrijednosti."""
        pass

    def setModelData(self, editor, model, index):
        """BITNA QT FUNKCIJA. u biti samo mora biti definirana, delegat ne postavlja
        vrijednosti."""
        pass

    def calculate_AB_for_row(self, x):
        """
        Ova funkcija definira što radi gumb. Računa i postavlja vrijednosti A (nagib
        korekcijskog pravca) i B (odsječak na osi y) iz podataka za zero/span.
        """
        # moramo pronaći view u kojem je embedan delegat.
        # sender je gumb, parent je "okvir/layout" u kojem se nalazi gumb, parent toga je tablica.
        # malo nespretno, ali radi
        view = self.sender().parent().parent()
        # kada imam view (tablicu), mogu pronaci model te tablice
        model = view.model()
        # i poziciju delegata u tablici
        indeks = view.indexAt(self.sender().pos())
        # poziv dijaloga za unos parametara za zero i span
        dijalog = ABDialog()
        ok = dijalog.exec_()
        # ako je dijalog prihvaćen...
        if ok:
            a, b = dijalog.AB # dohvati A i B
            model.set_AB_for_row(indeks.row(), a, b) # postavi vrijednosti u model
            # commitData je bitan jer signalizira promjenu tj. update tablice (view-a)
            self.commitData.emit(self.sender())

########### validator ##########################################################
class DoubleValidatedLineEdit(QtWidgets.QLineEdit):
    """
    Klasa koja definira line edit, ali takav da imamo validaciju za brojeve.
    """
    def __init__(self, val, parent=None):
        """Konstruktor klase"""
        super(DoubleValidatedLineEdit, self).__init__(parent=parent)
        self.setValidator(QtGui.QDoubleValidator())  # set validation for double characters
        self.setText(str(val))

########### dialog za računanje AB ##########################################
class ABDialog(QtWidgets.QDialog):
    """
    Klasa za dijalog - računanje parametara A (nagib korekcijskog pravca) i B (odsječak
    na osi y)
    """
    def __init__(self, parent=None):
        """Konstruktor klase"""
        super(ABDialog, self).__init__(parent=parent)
        self.setModal(False) # nije modalni dijalog
        self.setWindowTitle('Računanje A, B') # naziv dijaloga
        # OUTPUT VARS
        self._AB = (1.0, 0.0)
        # definiramo widgete za unos vrijednosti
        self.span0 = DoubleValidatedLineEdit(1.0, parent=self)
        self.span1 = DoubleValidatedLineEdit(1.0, parent=self)
        self.zero0 = DoubleValidatedLineEdit(0.0, parent=self)
        self.zero1 = DoubleValidatedLineEdit(0.0, parent=self)
        self.Aparam = DoubleValidatedLineEdit(1.0, parent=self)
        self.Bparam = DoubleValidatedLineEdit(0.0, parent=self)
        # result
        self.outputA = QtWidgets.QLabel('1.0')
        self.outputB = QtWidgets.QLabel('0.0')
        # gumbi za prihvaćanje / odbijanje dijaloga
        self.gumbOK = QtWidgets.QPushButton('Ok')
        self.gumbCancel = QtWidgets.QPushButton('Cancel')
        # slaganje widgeta u layout
        gridlay = QtWidgets.QGridLayout()
        gridlay.addWidget(QtWidgets.QLabel('span 0 :'), 0, 0, 1, 1)
        gridlay.addWidget(self.span0, 0, 1, 1, 1)
        gridlay.addWidget(QtWidgets.QLabel('zero 0 :'), 0, 2, 1, 1)
        gridlay.addWidget(self.zero0, 0, 3, 1, 1)
        gridlay.addWidget(QtWidgets.QLabel('span 1 :'), 1, 0, 1, 1)
        gridlay.addWidget(self.span1, 1, 1, 1, 1)
        gridlay.addWidget(QtWidgets.QLabel('zero 1 :'), 1, 2, 1, 1)
        gridlay.addWidget(self.zero1, 1, 3, 1, 1)
        gridlay.addWidget(QtWidgets.QLabel('A :'), 2, 0, 1, 1)
        gridlay.addWidget(self.Aparam, 2, 1, 1, 1)
        gridlay.addWidget(QtWidgets.QLabel('B :'), 2, 2, 1, 1)
        gridlay.addWidget(self.Bparam, 2, 3, 1, 1)
        gridlay.addWidget(QtWidgets.QLabel('Out A'), 3, 0, 1, 1)
        gridlay.addWidget(self.outputA, 3, 1, 1, 1)
        gridlay.addWidget(QtWidgets.QLabel('Out B'), 3, 2, 1, 1)
        gridlay.addWidget(self.outputB, 3, 3, 1, 1)
        gridlay.addWidget(self.gumbOK, 5, 2, 1, 1)
        gridlay.addWidget(self.gumbCancel, 5, 3, 1, 1)
        self.setLayout(gridlay)
        # povezivanje akcija widgeta sa callback funkcijama
        self.gumbOK.clicked.connect(self.accept)
        self.gumbCancel.clicked.connect(self.reject)
        self.span0.textChanged.connect(self.racunaj_AB)
        self.span1.textChanged.connect(self.racunaj_AB)
        self.zero0.textChanged.connect(self.racunaj_AB)
        self.zero1.textChanged.connect(self.racunaj_AB)
        self.Aparam.textChanged.connect(self.racunaj_AB)
        self.Bparam.textChanged.connect(self.racunaj_AB)

    @property
    def AB(self):
        """Getter rezultata : tuple (A, B) """
        return self._AB

    @AB.setter
    def AB(self, x):
        """Setter rezultata : tuple (A, B) """
        self._AB = x

    def showEvent(self, event):
        """
        Reimplement funkcije, prilikom prikazivanja dijaloga moramo resetati
        vrijednosti koje su unešene na default postavke.
        """
        self.reset_params()
        super(ABDialog, self).showEvent(event)

    def reset_params(self):
        """
        Funkcija resetira sva polja na defaultne postavke.
        """
        self.span0.setText('1.0')
        self.span1.setText('1.0')
        self.zero0.setText('0.0')
        self.zero1.setText('0.0')
        self.Aparam.setText('1.0')
        self.Bparam.setText('0.0')
        self.outputA.setText('1.0')
        self.outputB.setText('0.0')

    def racunaj_AB(self):
        """
        Callback funkcija za računanje parametara A, B. Prvo dohvaćamo vrijednosti
        iz polja za unos. Računamo vrijednost A, i B te spremamo rezultat.
        """
        try:
            # dohvati vrijednosti iz polja za unos
            s0, s1 = float(self.span0.text()), float(self.span1.text())
            z0, z1 = float(self.zero0.text()), float(self.zero1.text())
            ab = (float(self.Aparam.text()), float(self.Bparam.text()))
            # izračunaj
            outA, outB = self.calcab(s0, s1, z0, z1, ab)
            # postavi rezultate
            self.AB = (outA, outB)
            self.outputA.setText(str(outA))
            self.outputB.setText(str(outB))
        except ValueError:
            # slučaj prilikom pogreške u radu
            self.AB = (None, None)
            self.outputA.setText('None')
            self.outputB.setText('None')

    def calcab(self, s0, s1, z0, z1, ab):
        """pomoćna funkcija koja računa A B"""
        a = (s0 - z0) / (s1 - z1)
        b = z0 - a * z1
        aa = a * ab[0]
        bb = ab[0] * b + ab[1]
        return aa, bb
