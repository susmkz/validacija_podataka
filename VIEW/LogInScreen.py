#!/usr/bin/python3
# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets


class LogInDialog(QtWidgets.QDialog):
    """
    Klasa za login dijalog.
    """
    def __init__(self):
        """
        Konstruktor klase.
        """
        super(LogInDialog, self).__init__()

        # placeholders for username and password
        self.__user = ''
        self.__pass = ''

        self.initUI()

    def initUI(self):
        """
        Inijcalizacja dijaloga
        """
        self.setWindowTitle('Log in') # naziv prozora
        # labeli vezani uz polja za unos podataka
        self.__userLabel = QtWidgets.QLabel('user :')
        self.__passLabel = QtWidgets.QLabel('password :')
        # definicija line edit widgeta za unos podataka i connection
        self.__userLineEdit = QtWidgets.QLineEdit()
        self.__userLineEdit.textChanged.connect(self.update_user)
        self.__passLineEdit = QtWidgets.QLineEdit()
        # sakrij password polje sa maskom ****
        self.__passLineEdit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.__passLineEdit.textChanged.connect(self.update_pass)
        # ok and cancel gumbi i connect sa akcijama
        self.__buttonOK = QtWidgets.QPushButton('Ok')
        self.__buttonOK.clicked.connect(self.accept)
        self.__buttonCancel = QtWidgets.QPushButton('Cancel')
        self.__buttonCancel.clicked.connect(self.reject)
        # layouts
        self.__userlayout = QtWidgets.QHBoxLayout()
        self.__passlayout = QtWidgets.QHBoxLayout()
        self.__buttonlayout = QtWidgets.QHBoxLayout()
        self.__grouplayout = QtWidgets.QVBoxLayout()
        # postavljanje elemenata u layoute
        self.__userlayout.addWidget(self.__userLabel)
        self.__userlayout.addWidget(self.__userLineEdit)
        self.__passlayout.addWidget(self.__passLabel)
        self.__passlayout.addWidget(self.__passLineEdit)
        self.__buttonlayout.addStretch() # guramo gumbe na desno
        self.__buttonlayout.addWidget(self.__buttonOK)
        self.__buttonlayout.addWidget(self.__buttonCancel)
        # slaganje layouta u prozor
        self.__grouplayout.addLayout(self.__userlayout)
        self.__grouplayout.addLayout(self.__passlayout)
        self.__grouplayout.addLayout(self.__buttonlayout)
        self.setLayout(self.__grouplayout)

    def update_user(self, text):
        """
        Callback funkcija koja reagira na promjenu teksta u polju za unos korisnika.
        """
        self.__user = text

    def update_pass(self, text):
        """
        Callback funkcija koja reagira na promjenu teksta u polju za unos šifre.
        """
        self.__pass = text

    @property
    def credentials(self):
        """
        property dijaloga koji vraća tuple (username, password) koji je potreban za autorizaciju
        """
        return (self.__user, self.__pass)
