#!/usr/bin/python3
# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets


class SelectMeasurementDialog(QtWidgets.QDialog):
    """
    Klasa koja definira dijalog za izbor programa mjerenja (kanalId) i vremenskog
    perioda "od" - "do" za prikupljanje podataka sa REST servisa.

    Dialog class for selecting measurements and time period
    -needs a qt tree model of measurements
    -needs a instance of main window as it's parent
    """
    def __init__(self, tree, parent):
        """
        Konstruktor klase. Inicijalizacija treba qtTreeModel mjerenja (tree)
        i instancu glavnog prozora (parent).
        """
        super(SelectMeasurementDialog, self).__init__(parent)
        self.tree = tree
        self.selected = []
        self.timeStart = None
        self.timeEnd = None

        self.initUI()

    def initUI(self):
        """
        Funkcija za inicijalizaciju sučelja dijaloga. Definiranje widgeta i rada
        s istim.
        """
        # naziv dijaloga
        self.setWindowTitle('Izbor mjerenja')
        # definiramo kalendar widget za izbor vremena 'od' sa opisnim labelom
        self.labelStart = QtWidgets.QLabel('Vrijeme od :')
        self.kalendarStart = QtWidgets.QCalendarWidget()
        self.kalendarStart.setFirstDayOfWeek(QtCore.Qt.Monday)
        # definiramo kalendar widget za izbor vremena 'do' sa opisnim labelom
        self.labelEnd = QtWidgets.QLabel('Vrijeme do :')
        self.kalendarEnd = QtWidgets.QCalendarWidget()
        self.kalendarEnd.setFirstDayOfWeek(QtCore.Qt.Monday)
        # definiramo treeView za prikaz modela programa mjerenja
        self.treeView = QtWidgets.QTreeView()
        self.set_tree_model(self.tree) #link modela i view-a
        # definiramo gumb za prihvaćanje dijaloga
        self.buttonOK = QtWidgets.QPushButton('Ok')
        self.buttonOK.clicked.connect(self.reimplemented_accept)
        # definiramo gumb za odbijanje dijaloga
        self.buttonCancel = QtWidgets.QPushButton('Cancel')
        self.buttonCancel.clicked.connect(self.reject)
        # layouti za widgete
        self.vlay1 = QtWidgets.QVBoxLayout() #for calendars
        self.vlay2 = QtWidgets.QHBoxLayout() #will be main
        self.vlay3 = QtWidgets.QHBoxLayout() #buttons
        # postavljanje widgeta u layoute
        self.vlay1.addWidget(self.labelStart)
        self.vlay1.addWidget(self.kalendarStart)
        self.vlay1.addWidget(self.labelEnd)
        self.vlay1.addWidget(self.kalendarEnd)
        self.vlay3.addStretch()
        self.vlay3.addWidget(self.buttonOK)
        self.vlay3.addWidget(self.buttonCancel)
        self.vlay1.addLayout(self.vlay3)
        self.vlay2.addWidget(self.treeView)
        self.vlay2.addLayout(self.vlay1)
        # postavljanje glavnog layouta
        self.setLayout(self.vlay2)

    def set_tree_model(self, tree):
        """
        Postavljanje novog tree modela u dijalog.
        """
        self.tree = tree # zapamti novi model
        self.treeView.setModel(tree) # link model sa view-om
        # definiraj selection da omogućimo izbor više programa mjerenja
        self.treeView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        # reset izbor
        self.selected = []
        self.timeStart = self.kalendarStart.selectedDate()
        self.timeEnd = self.kalendarEnd.selectedDate()

    @property
    def selection(self):
        """
        Property vraća tuple:
        - liste izabranih programa mjerenja (kanalId)
        - qdate of start time
        - qdate of end time
        """
        return (self.selected, self.timeStart, self.timeEnd)

    def reimplemented_accept(self):
        """
        Reimplementacija accept funkcije (OK gumb na dijalogu). Ideja je presresti
        akciju accept koja služi za prihvaćanje dijaloga da bi napravili par provjera.
        Moramo zapamtiti koji su kanali izabrani te zapamtiti početno i završno
        vrijeme.
        """
        self.selected = [self.tree.data(i) for i in self.treeView.selectedIndexes() if i.column() == 2]
        self.timeStart = self.kalendarStart.selectedDate() # qdate instance
        self.timeEnd = self.kalendarEnd.selectedDate() # qdate instance
        # provjeri da li je izabrano neko mjerenje (kanal)
        if not self.selected:
            reply = QtWidgets.QMessageBox.warning(
                self,
                'Warning',
                'Izabreite barem jedan kanal za nastavak.',
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Ok)
            return #izlaz iz metode.. porzor treba ostati upaljen (ne šaljemo accept)
        # logička provjera, start vrijeme mora biti manje od vremena kraja
        if self.timeStart > self.timeEnd:
            reply = QtWidgets.QMessageBox.warning(
                self,
                'Warning',
                'Vrijeme početka je veće od vremena kraja.',
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Ok)
            return #izlaz iz metode.. porzor treba ostati upaljen (ne šaljemo accept)
        # prosljedimo prihvat OK predefiniranoj metodi
        self.accept()

