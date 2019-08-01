#!/usr/bin/python3
# -*- coding: utf-8 -*-

##############################################################################
#TODO! critical fails
# - POTENCIJALNI BUG PRILIKOM MJENJANJA FLAGA...
    #NO2 SPECIAL CASE (npr. NEDOSTAJE -? ne smijem se oslanjati na ucitani NO2 flag?) NOT TESTED
# - OMOGUĆITI BLAŽI LOGIČKI TEST ZA NOX?

#TODO!
#- EXTENSIVE TESTING NEEDED
#- REFACTOR : QTMODELS djele dosta zajedničke funkcionalnosti (trenutno su copy paste što je loše)
#- draw/correction/ sync redosljed bi mogao biti bolji
#- upute / pitfalls za rad sa aplikacijom
    # PM se u biti ne konvertiraju (konverzijski faktor je 1, tj. iako piše da je ppb i dalje je u ug/m3)
    # nakon loada sessiona moramo ponovno primjeniti korekciju...

#POPIS MODULA SA KRATKIM OPISOM
#MAIN
    #validacija.py - pokretač aplikacije
#app/QTMODELS
    #KoncentracijaModel.py - modeli za tablice koncentracijskih vrijednosti
    #SatniModel.py - modeli za tablice satno agregiranih vrijednosti (nakon korekcije)
    #StatistikaModel.py - model za prikaz statističkih podataka satno agregiranih vrijednosti
    #ZeroSpanModel.py - model za prikaz zero i span tablica
    #KorekcijaModel.py - modeli za prikaz tablica za unos korekcijskih parametara
    #TreeModel.py - tree model za prikaz izbora pojedinih kanala prilikom učitavanja sa REST-a
#app/KONFIG
    #Configuration.py - glavni konfiguracijski objekt aplikacie
#app/REST
    #RestCommunication.py - objekti za rad sa REST servisom
#app/DOCUMENT
    #Session.py - objekt za čuvanje sessiona aplikacije (radni set podataka)
    #Datastore.py - objet za čuvanje podataka pojedinog kanala (modeli...)
    #Document.py - glavni dokument aplikacije - load, save, new Session operacije idu preko njega + tree model
#app/VIEW
    #Canvas.py - objektna reprezentacija grafa na kojem se crtaju podaci
    #Display.py - unutarnji dio aplikacije (tablice, graf)
    #LogInScreen.py - dijalog za login
    #MainWindow.py - glavi prozor aplikacije (definiranje akcija, toolbarova...)
    #SelectScreen.py - dijalog za izbor podataka sa REST-a
    #TableViews.py - objekti za tablice - rad sa QT modelima.

#+6000 lines of code sa 24.7.2018.
##############################################################################
import sys
import logging
from PyQt5 import QtWidgets
from app.VIEW import MainWindow
from app.KONFIG import Configuration

def run_app():
    """Funkcija koja pokrece glavnu aplikaciju"""
    # ucitavanje glavnog konfiguracijskog file-a
    try:
        fajl = './app/KONFIG/konfig.cfg'
        konfig = Configuration.MainKonfig()
        konfig.read_konfig_file(fajl)
    except Exception as err:
        print('Pogreška prilikom čitanja konfiguracijskog file-a.')
        print(err)
        sys.exit(0) # force quit aplikacije

    # definiranje loggera
    try:
        level = konfig.get_konfig_option('LOG_SETUP', 'lvl', 'ERROR')
        level = konfig.LOG_LEVELS[level] # conversion to correct type
        filename = konfig.get_konfig_option('LOG_SETUP', 'file', './applog.log')
        mode = konfig.get_konfig_option('LOG_SETUP', 'mode', 'a')
        logging.basicConfig(
            handlers=[logging.FileHandler(filename, mode, 'utf-8')],
            level=level,
            format=u'{levelname}:::{asctime}:::{module}:::{funcName}:::{message}',
            style='{')
    except Exception as err:
        print('Pogreška prilikom čitanja konfiguracijskog file-a.')
        sys.exit(0) # force quit

    # postavljanje QApplication objekta (definiranje glavnog event loop-a)
    app = QtWidgets.QApplication(sys.argv)
    # postavljanje glavnog prozora
    glavniProzor = MainWindow.GlavniProzor(konfig)
    # kickstart aplikacije
    returnCode = app.exec_()
    # manualni cleanup varijabli (brisanje zaostalih Qt objekata)
    del glavniProzor
    del app
    # gasimo interpreter
    sys.exit(returnCode)


if __name__ == '__main__':
    run_app()
