#!/usr/bin/python3
# -*- coding: utf-8 -*-
import copy
import logging
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from app.VIEW.Display import Display
from app.VIEW.LogInScreen import LogInDialog
from app.VIEW.SelectScreen import SelectMeasurementDialog
from app.REST.RestCommunication import RESTZahtjev, DataReaderAndCombiner
from app.DOCUMENT.Document import Dokument
################################################################################
################## MainWindow - pocetak klase ##################################
################################################################################
class GlavniProzor(QtWidgets.QMainWindow):
    """
    Klasa za glavni prozor aplikacije. Definira akcije, menubar, toolbar ...
    """
    def __init__(self, konfig):
        """
        Konstruktor klase.
        """
        super(GlavniProzor, self).__init__()
        self.LOGGED_IN = False #logged in status
        self.CONFIGURATION = konfig #MAIN CONFIGURATION (REST, LOGGING ...)
        self.REST_REQUEST = RESTZahtjev(self.CONFIGURATION) #REST COMMUNICATION
        self.REST_READER = DataReaderAndCombiner(self.REST_REQUEST, self) #REST READER
        self.DOKUMENT = Dokument() #MAIN HOLDER OF DATA
        # trajni dijalog za izbor kanala sa REST-a
        self.SELECTION_DIALOG = SelectMeasurementDialog(self.DOKUMENT.treeModelProgramaMjerenja, self)
        # inicijalizacija grafičkog sučelja
        self.initUI()
    ############################################################################
    def initUI(self):
        """
        Inicijalizacija sučelja, definicija gumbi, akcija, widgeta...
        """
        self.setWindowTitle('Aplikacija za validaciju podataka')
        ################## ACTIONS ######################
        # exit action
        self.__exitAct = QtWidgets.QAction('Izlaz', self)
        self.__exitAct.setShortcut('Ctrl+Q')
        self.__exitAct.setStatusTip('Izlaz iz aplikacije.')
        self.__exitAct.setToolTip('Izlaz iz aplikacije.')
        self.__exitAct.triggered.connect(self.close)
        # ucitaj podatke sa REST-a
        self.__restReadAct = QtWidgets.QAction('Učitaj sa REST-a', self)
        self.__restReadAct.setStatusTip('Učitavanje podataka sa REST servisa.')
        self.__restReadAct.setToolTip('Učitavanje podataka sa REST servisa.')
        self.__restReadAct.triggered.connect(self.get_data_from_rest)
        # primjena korekcije
        self.__primjeniKorekcijuAct = QtWidgets.QAction('Primjeni korekciju', self)
        self.__primjeniKorekcijuAct.setStatusTip('Primjena korekcije na podatke.')
        self.__primjeniKorekcijuAct.setToolTip('Primjena korekcije na podatke.')
        self.__primjeniKorekcijuAct.triggered.connect(self.apply_correction)
        # log in action
        self.__loginAct = QtWidgets.QAction('Log in', self)
        self.__loginAct.setStatusTip('Log in u aplikaciju.')
        self.__loginAct.setToolTip('Log in u aplikaciju.')
        self.__loginAct.triggered.connect(self.log_in)
        # log out action
        self.__logoutAct = QtWidgets.QAction('Log out', self)
        self.__logoutAct.setStatusTip('Log out iz aplikacije.')
        self.__logoutAct.setToolTip('Log out iz aplikacije.')
        self.__logoutAct.triggered.connect(self.log_out)
        # reconnect action
        self.__reconnectAct = QtWidgets.QAction('Reconnect', self)
        self.__reconnectAct.setStatusTip('Ponovno spajanje na REST servis.')
        self.__reconnectAct.setToolTip('Ponovno spajanje na REST servis.')
        self.__reconnectAct.triggered.connect(self.reconnect_to_REST)
        # toggle tool bar
        self.__toggleToolBarAct = QtWidgets.QAction('Pokaži alatnu traku.', self)
        self.__toggleToolBarAct.setStatusTip('Prikazivanje/skrivanje alatne trake.')
        self.__toggleToolBarAct.setToolTip('Prikazivanje/skrivanje alatne trake.')
        self.__toggleToolBarAct.setCheckable(True)
        self.__toggleToolBarAct.setChecked(True)
        self.__toggleToolBarAct.triggered.connect(self.toggle_tool_bar_visibility)
        # load correction parameters
        self.__loadCorrectionParametersAct = QtWidgets.QAction('Učitaj parametre korekcije', self)
        self.__loadCorrectionParametersAct.setStatusTip('Učitavanje parametara korekcije iz csv file-a.')
        self.__loadCorrectionParametersAct.setToolTip('Učitavanje parametara korekcije iz csv file-a.')
        self.__loadCorrectionParametersAct.triggered.connect(self.load_correction_parameters)
        # save correction parameters
        self.__saveCorrectionParametersAct = QtWidgets.QAction('Spremi parametre korekcije', self)
        self.__saveCorrectionParametersAct.setStatusTip('Spremanje parametara korekcije u csv file.')
        self.__saveCorrectionParametersAct.setToolTip('Spremanje parametara korekcije u csv file.')
        self.__saveCorrectionParametersAct.triggered.connect(self.save_correction_parameters)
        # load previous session
        self.__loadSessionAct = QtWidgets.QAction('Učitaj session', self)
        self.__loadSessionAct.setStatusTip('Učitavanje session-a iz file-a.')
        self.__loadSessionAct.setToolTip('Učitavanje session-a iz file-a.')
        self.__loadSessionAct.setShortcut('Ctrl+L')
        self.__loadSessionAct.triggered.connect(self.load_session)
        # save session
        self.__saveSessionAct = QtWidgets.QAction('Spremi session', self)
        self.__saveSessionAct.setStatusTip('Spremanje session-a u file.')
        self.__saveSessionAct.setToolTip('Spremanje session-a u file.')
        self.__saveSessionAct.setShortcut('Ctrl+S')
        self.__saveSessionAct.triggered.connect(self.save_session)
        # save sirove podatke to file (minutni podatci)
        self.__saveRawDataToFileAct = QtWidgets.QAction('Spremi minutne', self)
        self.__saveRawDataToFileAct.setStatusTip("Spremanje ulaznih podataka u file")
        self.__saveRawDataToFileAct.setToolTip("Spremanje ulaznih podataka u file")
        self.__saveRawDataToFileAct.triggered.connect(self.save_raw_data_to_file)
        # save validated data to file (satno agregirani)
        self.__saveValidatedDataToFileAct = QtWidgets.QAction('Spremi validirane', self)
        self.__saveValidatedDataToFileAct.setStatusTip('Spremanje validiranih, satno agregiranih podataka u file.')
        self.__saveValidatedDataToFileAct.setToolTip('Spremanje validiranih, satno agregiranih podataka u file.')
        self.__saveValidatedDataToFileAct.triggered.connect(self.save_validated_to_file)
        # save validated data to REST
        self.__saveValidatedDataToRESTAct = QtWidgets.QAction('Spremi validirane na REST', self)
        self.__saveValidatedDataToRESTAct.setStatusTip('Spremanje validiranih, satno agregiranih podataka na REST.')
        self.__saveValidatedDataToRESTAct.setToolTip('Spremanje validiranih, satno agregiranih podataka na REST.')
        self.__saveValidatedDataToRESTAct.triggered.connect(self.save_validated_to_REST)
        # version information & licence
        self.__versionAndLicenceInfo = QtWidgets.QAction('O aplikaciji')
        self.__versionAndLicenceInfo.setStatusTip('Prikaz informacija o aplikaciji')
        self.__versionAndLicenceInfo.setToolTip('Prikaz informacija o aplikaciji')
        self.__versionAndLicenceInfo.triggered.connect(self.pokazi_informacije_o_aplikaciji)
        ################## MENU BAR ######################
        self.__menubar = self.menuBar()
        # File menu
        self.__fileMenu = self.__menubar.addMenu('&File')
        self.__fileMenu.addAction(self.__saveSessionAct)
        self.__fileMenu.addAction(self.__loadSessionAct)
        self.__fileMenu.addSeparator()
        self.__fileMenu.addAction(self.__primjeniKorekcijuAct)
        self.__fileMenu.addAction(self.__saveCorrectionParametersAct)
        self.__fileMenu.addAction(self.__loadCorrectionParametersAct)
        self.__fileMenu.addSeparator()
        self.__fileMenu.addAction(self.__saveRawDataToFileAct)
        self.__fileMenu.addAction(self.__saveValidatedDataToFileAct)
        self.__fileMenu.addSeparator()
        self.__fileMenu.addAction(self.__exitAct)
        # REST menu
        self.__restMenu = self.__menubar.addMenu('&REST')
        self.__restMenu.addAction(self.__loginAct)
        self.__restMenu.addAction(self.__logoutAct)
        self.__restMenu.addSeparator()
        self.__restMenu.addAction(self.__reconnectAct)
        self.__restMenu.addSeparator()
        self.__restMenu.addAction(self.__restReadAct)
        self.__restMenu.addAction(self.__saveValidatedDataToRESTAct)
        # View menu
        self.__viewMenu = self.__menubar.addMenu('View')
        self.__viewMenu.addAction(self.__toggleToolBarAct)
        self.__viewMenu.addAction(self.__versionAndLicenceInfo)
        ################## TOOL BAR ########################
        self.__toolBar = self.addToolBar('Tools')
        self.__toolBar.addAction(self.__restReadAct)
        self.__toolBar.addSeparator()
        self.__toolBar.addAction(self.__saveSessionAct)
        self.__toolBar.addAction(self.__loadSessionAct)
        self.__toolBar.addSeparator()
        self.__toolBar.addAction(self.__primjeniKorekcijuAct)
        self.__toolBar.addAction(self.__saveCorrectionParametersAct)
        self.__toolBar.addAction(self.__loadCorrectionParametersAct)
        self.__toolBar.addSeparator()
        self.__toolBar.addAction(self.__saveRawDataToFileAct)
        self.__toolBar.addAction(self.__saveValidatedDataToFileAct)
        self.__toolBar.addAction(self.__saveValidatedDataToRESTAct)
        ################## STATUS BAR ######################
        self.__statusBar = self.statusBar()
        self.__statusBar.showMessage('Ready', 3000)
        ################## CENTRAL WIDGET ##################
        self.centralniWidget = Display()
        self.setCentralWidget(self.centralniWidget)

        self.showMaximized()
        self.toggle_logged_in_state(False)
        self.__statusBar.showMessage('Ready', 3000)

    def toggle_logged_in_state(self, state):
        """
        Prebaci gui u log in / out state.
        -ako je user loged out jedino je log in opcija aktivna, sve druge su neaktivne
        -ako je user loged in dozvoli REST akcije, ali disable log in akciju
        """
        self.__loginAct.setEnabled(not state)
        self.LOGGED_IN = state
        self.__reconnectAct.setEnabled(state)
        self.__restReadAct.setEnabled(state)
        self.__saveValidatedDataToRESTAct.setEnabled(state)
        self.__logoutAct.setEnabled(state)

    ############################################################################
    ####################### ACTION CALLBACKS ###################################
    ############################################################################
    def save_session(self):
        """
        Spremi aktivni dokument u file. Serijalizacija svih podataka potrebnih
        za rekonstrukciju stanja aplikacije.
        """
        # dijalog za izbor naziva file-a
        options = QtWidgets.QFileDialog.Options()
        filename, extension = QtWidgets.QFileDialog.getSaveFileName(parent=self,
                                                                    caption="Save session to file",
                                                                    options=options,
                                                                    filter="Sessions (*.dat);;All files (*.*)")
        if filename:
            # file je izabran, valja paziti na ekstenzije...
            if ('Sessions' in extension) and (not filename.endswith(".dat")):
                filename = filename + ".dat"
            # delegiraj spremanje dokumentu aplikacije
            try:
                # turn on wait cursor
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                self.__statusBar.showMessage('Spremanje sessiona ...', 3000)
                self.DOKUMENT.save_session(filename)
            except Exception as err:
                logging.error(str(err), exc_info=True)
            finally:
                # turn off wait cursor
                QtWidgets.QApplication.restoreOverrideCursor()

    def load_session(self):
        """
        Ucitaj dokument iz file-a. Serijalizacija svih podataka potrebnih
        za rekonstrukciju stanja aplikacije i postavljanje istih u aktivni dokument.
        """
        # dijalog za izbor naziva file-a
        options = QtWidgets.QFileDialog.Options()
        filename, extension = QtWidgets.QFileDialog.getOpenFileName(parent=self,
                                                                    caption="Load session from file",
                                                                    options=options,
                                                                    filter="Sessions (*.dat);;All files (*.*)")

        if filename:
            # file je izabran
            try:
                #turn on wait cursor
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                self.__statusBar.showMessage('Ucitavanje sessiona ...', 3000)
                #delegacija dokumentu za load/update
                self.DOKUMENT.load_session(filename)
                #prosljedi session iz dokumenta Display-u (centralniWidget je instanca objekta Display)
                self.centralniWidget.set_session(self.DOKUMENT.session)
            except Exception as err:
                logging.error(str(err), exc_info=True)
            finally:
                # turn off wait cursor
                QtWidgets.QApplication.restoreOverrideCursor()

    def apply_correction(self):
        """
        primjena korekcije
        Prosljedi zahtjev za primjenom korekcije objektu Display (centralniWidget)
        """
        try:
            # turn on wait cursor
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.__statusBar.showMessage('Primjena korekcije ...', 3000)
            self.centralniWidget.primjeni_korekciju()
        except Exception as err:
            logging.error(str(err), exc_info=True)
        finally:
            # turn off wait cursor
            QtWidgets.QApplication.restoreOverrideCursor()

    def save_correction_parameters(self):
        """
        Spremanje tablice korekcijskih parametara u csv file.
        """
        # izbor kanala iz kojeg spremamo tablicu
        mapaKanala = self.DOKUMENT.session.get_mapu_kanala_ID_OPIS()
        inverzMapaKanala = dict(zip(mapaKanala.values(), mapaKanala.keys()))
        opisi = list(mapaKanala.values())
        kanali = list(mapaKanala.keys())

        izabraniKanal = None
        if len(mapaKanala) == 0:
            #nista nije ucitano
            izabraniKanal = None
        elif len(mapaKanala) == 1:
            #imamo samo jedan kanal, nema smisla prikazati dijalog
            izabraniKanal = kanali[0]
        else:
            # dijalog za izbor kanala (TABA) kojeg spremamo
            izabraniOpis, ok = QtWidgets.QInputDialog.getItem(self,
                                                              "Spremanje korekcijske tablice, izbor kanala.",
                                                              "Kanal",
                                                              opisi,
                                                              0,
                                                              editable=False)
            if ok:
                izabraniKanal = inverzMapaKanala[izabraniOpis]
        if izabraniKanal != None:
            # popup za izbor filename za korekcijsku tablicu
            options = QtWidgets.QFileDialog.Options()
            filename, extension = QtWidgets.QFileDialog.getSaveFileName(parent=self,
                                                                        caption="Spremanje tablice korekcijskih parametara u file.",
                                                                        options=options,
                                                                        filter="CSV file (*.csv)")
            if filename:
                # file je izabran, valja paziti na ekstenzije...
                if not filename.endswith(".csv"):
                    filename = filename + ".csv"
                # spremanje u csv file ...
                try:
                    # turn on wait cursor
                    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                    self.__statusBar.showMessage('Spremanje korekcijskih parametara ...', 3000)
                    tablica = self.DOKUMENT.session.get_datastore(izabraniKanal).korekcija.dataframe
                    # naći mjernu jedinicu i dodati je na kraj frejma
                    jedinica = self.DOKUMENT.session.get_datastore(izabraniKanal).korekcija.jedinica
                    tablica['jedinica'] = str(jedinica)
                    # zapis u file
                    tablica.to_csv(filename, sep=';')
                except Exception as err:
                    logging.error(str(err), exc_info=True)
                finally:
                    # turn off wait cursor
                    QtWidgets.QApplication.restoreOverrideCursor()

    def load_correction_parameters(self):
        """
        Učitavanje tablice korekcijskih parametara iz csv file-a.
        """
        # izbor kanala u kojeg spremamo tablicu
        mapaKanala = self.DOKUMENT.session.get_mapu_kanala_ID_OPIS()
        inverzMapaKanala = dict(zip(mapaKanala.values(), mapaKanala.keys()))
        opisi = list(mapaKanala.values())
        kanali = list(mapaKanala.keys())

        izabraniKanal = None
        if len(mapaKanala) == 0:
            # nista nije ucitano
            izabraniKanal = None
        elif len(mapaKanala) == 1:
            # imamo samo jedan kanal, nema smisla prikazati dijalog
            izabraniKanal = kanali[0]
        else:
            izabraniOpis, ok = QtWidgets.QInputDialog.getItem(self,
                                                              "Ucitavanje korekcijske tablice, izbor kanala.",
                                                              "Kanal",
                                                              opisi,
                                                              0,
                                                              editable=False)
            if ok:
                izabraniKanal = inverzMapaKanala[izabraniOpis]
        if izabraniKanal != None:
            # popup za izbor filename za korekcijsku tablicu
            options = QtWidgets.QFileDialog.Options()
            filename, extension = QtWidgets.QFileDialog.getOpenFileName(parent=self,
                                                                        caption="Učitavanje tablice korekcijskih parametara iz file-a.",
                                                                        options=options,
                                                                        filter="CSV file (*.csv)")
            if filename:
                # file je izabran, valja paziti na ekstenzije...
                if not filename.endswith(".csv"):
                    filename = filename + ".csv"
                try:
                    # turn on wait cursor
                    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                    self.__statusBar.showMessage('Ucitavanje korekcijskih parametara ...', 3000)
                    # citanje iz csv filea ... force konverziju u pandas datetime za stupac "vrijeme"
                    tablica = pd.read_csv(filename, sep=';', parse_dates=['vrijeme'])
                   
                    if len(tablica) == 0:
                        # TABLICA JE PRAZNA - restore cursor, info prozor da je tablica prazna, return
                        QtWidgets.QApplication.restoreOverrideCursor()
                        reply = QtWidgets.QMessageBox.information(
                                self,
                                'Information',
                                'Tablica korekcijskih parametara je prazna.',
                                QtWidgets.QMessageBox.Ok,
                                QtWidgets.QMessageBox.Ok)
                        return
                    if 'jedinica' not in tablica.columns:
                        # NEMA STUPCA SA JEDINICAMA - restore cursor, info prozor sa bugom, return
                        QtWidgets.QApplication.restoreOverrideCursor()
                        reply = QtWidgets.QMessageBox.information(
                                self,
                                'Information',
                                'U tablici nedostaje stupac "jedinica".',
                                QtWidgets.QMessageBox.Ok,
                                QtWidgets.QMessageBox.Ok)
                        return
                    # dohvati jedinicu - prvu iz tablice
                    jedinica = tablica['jedinica'][0]
                    aktivna_jedinica = self.centralniWidget.AKTIVNE_JEDINICE
                    if jedinica != aktivna_jedinica:
                        # MISSMATCH JEDINICA - restore cursor, info prozor sa bugom, return
                        QtWidgets.QApplication.restoreOverrideCursor()
                        reply = QtWidgets.QMessageBox.information(
                                self,
                                'Information',
                                'Mjerne jedinice ne odgovaraju - učitajte podatke u {0}.'.format(aktivna_jedinica),
                                QtWidgets.QMessageBox.Ok,
                                QtWidgets.QMessageBox.Ok)
                        return
                    # drop stupac sa jedinicom
                    tablica.drop('jedinica', axis=1, inplace=True)
                    # postavi u datastore objekta za korekciju
                    self.DOKUMENT.session.get_datastore(izabraniKanal).korekcija.dataframe = tablica
                except Exception as err:
                    logging.error(str(err), exc_info=True)
                finally:
                    # turn off wait cursor
                    QtWidgets.QApplication.restoreOverrideCursor()

    def save_raw_data_to_file(self):
        """
        Spremi sirove minutne podatke (ulazni podaci za računanje) u csv tablicu.
        """
        # izbor kanala iz kojeg spremamo tablicu
        mapaKanala = self.DOKUMENT.session.get_mapu_kanala_ID_OPIS()
        inverzMapaKanala = dict(zip(mapaKanala.values(), mapaKanala.keys()))
        opisi = list(mapaKanala.values())
        kanali = list(mapaKanala.keys())

        izabraniKanal = None
        if len(mapaKanala) == 0:
            #nista nije ucitano
            pass
        elif len(mapaKanala) == 1:
            # postoji samo jedan ucitani kanal, nema smisla prikazivati dijalog
            izabraniKanal = kanali[0]
        else:
            # postoji vise kanala, prikaz dijaloga za dodatni izbor
            izabraniOpis, ok = QtWidgets.QInputDialog.getItem(self,
                                                              "Spremanje ulaznih podataka, izbor kanala.",
                                                              "Kanal",
                                                              opisi,
                                                              0,
                                                              editable=False)
            if ok:
                izabraniKanal = inverzMapaKanala[izabraniOpis]
        
        if izabraniKanal != None:
            #popup dijalog za izbor naziva filea za tablicu
            options = QtWidgets.QFileDialog.Options()
            filename, extension = QtWidgets.QFileDialog.getSaveFileName(parent=self,
                                                                        caption="Spremanje ulaznih podataka.",
                                                                        options=options,
                                                                        filter="CSV file (*.csv)")
            if filename:
                #file je izabran, pripaziti na ekstenziju
                if not filename.endswith(".csv"):
                    filename = filename + ".csv"
                try:
                    #turn on wait cursor...
                    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                    self.__statusBar.showMessage('Spremanje ulaznih podataka ...', 3000)
                    #spremamo u file
                    tablica = self.DOKUMENT.session.get_datastore(izabraniKanal).koncentracija.dataframe
                    # dodati mjernu jedinicu ..
                    jedinica = self.DOKUMENT.session.get_datastore(izabraniKanal).koncentracija.jedinica
                    tablica['jedinica'] = str(jedinica)
                    # write out file
                    tablica.to_csv(filename, sep=';')
                except Exception as err:
                    logging.error(str(err), exc_info=True)
                finally:
                    #restore cursor
                    QtWidgets.QApplication.restoreOverrideCursor()

    def save_validated_to_file(self):
        """
        Spremi validirane, satno agregirane podatke u csv tablicu.
        """
        # izbor kanala iz kojeg spremamo tablicu
        mapaKanala = self.DOKUMENT.session.get_mapu_kanala_ID_OPIS()
        inverzMapaKanala = dict(zip(mapaKanala.values(), mapaKanala.keys()))
        opisi = list(mapaKanala.values())
        kanali = list(mapaKanala.keys())

        izabraniKanal = None
        if len(mapaKanala) == 0:
            # nista nije ucitano
            pass
        elif len(mapaKanala) == 1:
            # imamo samo jedan kanal, nema smisla prikazati dijalog
            izabraniKanal = kanali[0]
        else:
            izabraniOpis, ok = QtWidgets.QInputDialog.getItem(self,
                                                              "Spremanje validiranih i satno agregiranih podataka, izbor kanala.",
                                                              "Kanal",
                                                              opisi,
                                                              0,
                                                              editable=False)
            if ok:
                izabraniKanal = inverzMapaKanala[izabraniOpis]
        if izabraniKanal != None:
            # popup za izbor filename za tablicu
            options = QtWidgets.QFileDialog.Options()
            filename, extension = QtWidgets.QFileDialog.getSaveFileName(parent=self,
                                                                        caption="Spremanje validiranih i satno agregiranih podataka.",
                                                                        options=options,
                                                                        filter="CSV file (*.csv)")
            if filename:
                # file je izabran, valja paziti na ekstenzije...
                if not filename.endswith(".csv"):
                    filename = filename + ".csv"
                try:
                    # turn on wait cursor
                    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                    self.__statusBar.showMessage('Spremanje validiranih, stano agregiranih podataka ...', 3000)
                    # spremanje u csv file ...
                    tablica = self.DOKUMENT.session.get_datastore(izabraniKanal).satni.dataframe
                    # dodati mjernu jedinicu ..
                    jedinica = self.DOKUMENT.session.get_datastore(izabraniKanal).satni.jedinica
                    tablica['jedinica'] = str(jedinica)
                    #write out file
                    tablica.to_csv(filename, sep=';')
                except Exception as err:
                    logging.error(str(err), exc_info=True)
                finally:
                    # turn off wait cursor
                    QtWidgets.QApplication.restoreOverrideCursor()

    def closeEvent(self, event):
        """
        Reimplementiran close event, pitanje za provjeru namjere prije izlaza.
        """
        reply = QtWidgets.QMessageBox.question(
            self,
            'Message',
            "Da li ste sigurni da želite ugasiti aplikaciju? Podaci koji nisu spremljeni biti će izgubljeni.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def log_in(self):
        """
        Prikazi dijalog za log in, te prosljedi user i pass REST_REQUEST objektu
        """
        if not self.LOGGED_IN:
            dijalog = LogInDialog()
            returnCode = dijalog.exec()
            if returnCode:
                self.__statusBar.showMessage('log in ...', 2000)
                self.REST_REQUEST.logmein(dijalog.credentials)
                self.toggle_logged_in_state(True)
                self.reconnect_to_REST()
            else:
                self.__statusBar.showMessage('log in prekinut ...', 2000)
            del dijalog # izbriši dijalog
        else:
            reply = QtWidgets.QMessageBox.information(
                self,
                'Information',
                'Neki korisnik je aktivan, log out je potreban prije promjene korisnika.',
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Ok)

    def log_out(self):
        """Log out iz aplikacije, korisnicki podaci se brisu iz REST_REQUEST objekta"""
        if self.LOGGED_IN:
            self.__statusBar.showMessage('log out ...', 2000)
            self.REST_REQUEST.logmeout()
            self.toggle_logged_in_state(False)
        else:
            reply = QtWidgets.QMessageBox.information(
                self,
                'Information',
                'Nitko nije ulogiran u aplikaciju. Logout nije smislen.',
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Ok)

    def reconnect_to_REST(self):
        """
        Povuci nove podatke za postaje/mjerenja sa REST-a. Postavi novu "tree" strukturu mjerenja.
        """
        if self.LOGGED_IN:
            try:
                # postavi novi rest reader objekt
                self.REST_READER = DataReaderAndCombiner(self.REST_REQUEST, self)
                # get new programe mjerenja
                self.DOKUMENT.mjerenja = self.REST_REQUEST.get_programe_mjerenja()
                # set new tree into selectionDialog
                self.SELECTION_DIALOG.set_tree_model(self.DOKUMENT.treeModelProgramaMjerenja)
            except Exception as err:
                logging.error(str(err))
        else:
            reply = QtWidgets.QMessageBox.information(
                self,
                'Information',
                'Napravi login prije pokušaja spajanja na REST servis.',
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Ok)

    def get_data_from_rest(self):
        """
        Preuzimanje podataka sa REST-a. Prikaz izborkika za kanal/e te vremenski period.
        Spremanje preuzetih podataka u novi Session.
        """
        if not self.LOGGED_IN:
            reply = QtWidgets.QMessageBox.information(
                self,
                'Information',
                'Napravi login prije pokušaja spajanja na REST servis.',
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Ok)
            return
        # dohvati zadnje izmjene za kanale
        self.reconnect_to_REST()
        # show selection dialog
        reply = self.SELECTION_DIALOG.exec()
        try:
            if reply:
                kanali, vrijemeOd, vrijemeDo = self.SELECTION_DIALOG.selection
                # provjeri izbor za povezane kanale...
                sviKanali = self.DOKUMENT.provjeri_grupu_kanala(kanali)
                # pripremimo mapu koju trebamo dati za inicijalizaciju Session-a
                newSessionMap = {}
                statusMap = self.REST_REQUEST.get_statusMap() # dohvati decode mapu za statuse int2str
                self.__statusBar.showMessage('Preuzimanje podataka sa REST-a ...', 3000)
                for kanal in sviKanali:
                    konc, zero, span = self.REST_READER.get_data(kanal, vrijemeOd, vrijemeDo)
                    newSessionMap[kanal] = {} # stvori novu mapu za Session
                    newSessionMap[kanal]['kanalId'] = kanal
                    newSessionMap[kanal]['status_code'] = statusMap
                    newSessionMap[kanal]['broj_u_satu'] = self.REST_REQUEST.get_broj_u_satu(kanal) #broj podataka u satu
                    newSessionMap[kanal]['metaData'] = copy.deepcopy(self.DOKUMENT.mjerenja[kanal])
                    newSessionMap[kanal]['koncentracija'] = konc
                    newSessionMap[kanal]['zero'] = zero
                    newSessionMap[kanal]['span'] = span
                    newSessionMap[kanal]['korekcija'] = pd.DataFrame()
                # newSessionMap je gotov, postavi ga u dokument za generiranje novog Session objekta
                self.DOKUMENT.new_session(newSessionMap)
                # postavi novi session iz dokumenta u Display objekt (centralniWidget)
                self.centralniWidget.set_session(self.DOKUMENT.session)
        except Exception as err:
            logging.error(str(err), exc_info=True)
            reply = QtWidgets.QMessageBox.warning(
                    self,
                    'Warning',
                    'Problem kod učitavanja podataka.\n'+str(err),
                    QtWidgets.QMessageBox.Ok,
                    QtWidgets.QMessageBox.Ok)
   

    def save_validated_to_REST(self):
        """
        Spremanje validiranih podataka na REST - nije implementirano
        """
        reply = QtWidgets.QMessageBox.information(
            self,
            'Information',
            'Spremanje validiranih podataka na REST servis jos nije implementirano.',
            QtWidgets.QMessageBox.Ok,
            QtWidgets.QMessageBox.Ok)

    def toggle_tool_bar_visibility(self, state):
        """
        Funkcija za toggle vidljivosti alatne trake
        """
        if state:
            self.__toolBar.show()
        else:
            self.__toolBar.hide()


    def pokazi_informacije_o_aplikaciji(self):
        """
        Prikaz informacija o aplikaciji i licenca
        - verzija aplikacije
        - library o kojima app ovisi
        - licence (LGPLv3)
        """
        tekst_prozora = """
        <!DOCTYPE html>
        <html>
        
        <head>
            <title>Aplikacija za validaciju podataka kvalitete zraka</title>
        </head>
        
        <body>
            <h3><b>Aplikacija za validaciju podataka kvalitete zraka</b></h3>
            <p>verzija = 0.9.1\n</p>
            
            <p>Aplikacija je pisana u programskom jeziku <b>Python (v. 3.7)</b></p>
            <p>Aplikacija koristi eksterne programske pakete koji nisu zapakirani sa aplikacijom te ih je potrebno prethodno instalirati</p>
            <p>Potrebni porgramski paketi: \n\n</p>
            
            <table>
                <tr>
                    <th>Library</th>
                    <th>Version</th>
                </tr>
                <tr>
                    <td>numpy</td>
                    <td>1.15.2</td>
                </tr>
                <tr>
                    <td>pandas</td>
                    <td>0.23.4</td>
                </tr>
                <tr>
                    <td>requests</td>
                    <td>2.19.1</td>
                </tr>
                <tr>
                    <td>matplotlib</td>
                    <td>3.0.0</td>
                </tr>
                <tr>
                    <td>PyQt5</td>
                    <td>5.11.3</td>
                </tr>
            </table>       
        </body>
        </html>
        """
        reply = QtWidgets.QMessageBox.information(
                self,
                'Informacije o aplikaciji',
                tekst_prozora,
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Ok)
        return
