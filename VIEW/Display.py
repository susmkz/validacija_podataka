#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import warnings
import numpy as np
from PyQt5 import QtCore, QtWidgets
from app.VIEW.TableViews import ConcentrationsTableView, CorrectionsTableView, ConcentrationsSatniTableView, StatistikaTableView, CorrectionsTableViewNO2
from app.VIEW.Canvas import Kanvas, MyPlotNavigation
from app.QTMODELS.StatistikaModel import StatistikaTablica

class Display(QtWidgets.QWidget):
    """
    Klasa za "unutarnji" display prozor aplikacije koji je ugnježđen u glavni prozor.
    Sadrži grafove i tablice. Također, klasa je zadužena za primjenu korekcije i
    promjenu flaga zbog logike prilikom rada sa povezanim kanalima (NOx grupa, PM grupa).
    """
    def __init__(self, parent=None):
        """
        Konstruktor klase.
        """
        super(Display, self).__init__(parent=parent)

        self.AKTIVNE_JEDINICE = 'ug/m3' # jedinice u kojima radimo - masena koncentracija (ug/m3) ili parts per x ('ppb')
        self.session = None # aktivni Session (podaci o broju i vrsti mjerenja, podaci ...)
        self.concentrationTableViews = {} # skup QTabWiew objekata za tablice koncentracije
        self.concentrationSatniTableViews = {} # skup QTabView objekata za satno agregirane
        self.correctionTableViews = {} # skup QTabView objekata za korekcijske tablice
        self.statisticsTableView = StatistikaTableView() # tablica za prikaz statistickih podataka
        self.statisticsTableModel = StatistikaTablica() # qt model za statisticke podatke
        self.statisticsTableView.setModel(self.statisticsTableModel) # povezivanje statistickog modela i tablice
        ################ DEFINIRANJE DISPLAY KOMPONENTI  #######################
        # imamo 3 TAB WIDGETA (po jedan za koncentraciju, satno agregirane i korekciju)
        # u svaki od tih tab widgeta ide jedna tablica po kanalu u zasebni tab (iz view skupa)
        self.concentrationTabWidget = QtWidgets.QTabWidget() # TAB WIDGET ZA KONCENTRACIJE
        self.concentrationSatniTabWidget = QtWidgets.QTabWidget() # TAB WIDGET ZA SATNO AGREGIRANE
        self.correctionTabWidget = QtWidgets.QTabWidget() # TAB WIDGET ZA KOREKCIJSKE TABLICE
        self.kanvas = Kanvas(parent=self) # GRAF
        self.plotNavigation = MyPlotNavigation(self.kanvas, self) # NAVIGACIJSKI TOOLBAR ZA GRAF
        # grupa za pretvaranje jedinica
        self.unitToggleBox = QtWidgets.QGroupBox('Mjerne jedinice')
        self.radioUGM3 = QtWidgets.QRadioButton('ug/m3')
        self.radioPPB = QtWidgets.QRadioButton('ppb')
        self.unitToggleLayout = QtWidgets.QHBoxLayout()
        self.unitToggleLayout.addWidget(self.radioUGM3)
        self.unitToggleLayout.addWidget(self.radioPPB)
        self.unitToggleBox.setLayout(self.unitToggleLayout)
        self.radioUGM3.setChecked(True) #default je izbor u ug/m3
        ########################################################################
        #labeling tablica...
        #widget za tabove koncentracija
        self.koncTableKontejner = QtWidgets.QWidget()
        self.koncTableLabel = QtWidgets.QLabel('<b>Podaci</b>')
        self.koncTableKontejnerLayout = QtWidgets.QVBoxLayout()
        self.koncTableKontejnerLayout.addWidget(self.koncTableLabel)
        self.koncTableKontejnerLayout.addWidget(self.concentrationTabWidget)
        self.koncTableKontejner.setLayout(self.koncTableKontejnerLayout)
        #widget za tabove satno agregiranih
        self.satniTableKontejner = QtWidgets.QWidget()
        self.satniTableLabel = QtWidgets.QLabel('<b>Satno agregirani podaci</b>')
        self.satniTableKontejnerLayout = QtWidgets.QVBoxLayout()
        self.satniTableKontejnerLayout.addWidget(self.satniTableLabel)
        self.satniTableKontejnerLayout.addWidget(self.concentrationSatniTabWidget)
        self.satniTableKontejner.setLayout(self.satniTableKontejnerLayout)
        #widget za korekcijsku tablicu
        self.korrTableKontejner = QtWidgets.QWidget()
        self.korrTableLabel = QtWidgets.QLabel('<b>Korekcijska tablica</b>')
        self.korrTableKontejnerLayout = QtWidgets.QVBoxLayout()
        self.korrTableKontejnerLayout.addWidget(self.korrTableLabel)
        self.korrTableKontejnerLayout.addWidget(self.correctionTabWidget)
        self.korrTableKontejner.setLayout(self.korrTableKontejnerLayout)
        #widget za statističku tablicu
        self.statTableKontejner = QtWidgets.QWidget()
        self.statTableLabel = QtWidgets.QLabel('<b>Statistika satno agregiranih</b>')
        self.statTableKontejnerLayout = QtWidgets.QVBoxLayout()
        self.statTableKontejnerLayout.addWidget(self.statTableLabel)
        self.statTableKontejnerLayout.addWidget(self.statisticsTableView)
        self.statTableKontejner.setLayout(self.statTableKontejnerLayout)
        # labeling end
        ########################################################################
        # plot navigation toolbar moramo posložiti sa gumbima za promjenu jedinice
        self.combinedNavigationUnit = QtWidgets.QWidget()
        self.combinedNavigationUnitLayout = QtWidgets.QHBoxLayout()
        self.combinedNavigationUnitLayout.addWidget(self.plotNavigation)
        self.combinedNavigationUnitLayout.addWidget(self.unitToggleBox)
        self.combinedNavigationUnit.setLayout(self.combinedNavigationUnitLayout)
        # prije slaganja elemenata u layout definiramo "splittere" u koje ćemo slagati komponente
        self.splitter0 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.splitter1 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter2 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.splitter3 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        # splitter0 je vertikalni split izmedju minutnih i satnih podataka
        #self.splitter0.addWidget(self.concentrationTabWidget)
        #self.splitter0.addWidget(self.concentrationSatniTabWidget)
        # insert widgeta sa labelima
        self.splitter0.addWidget(self.koncTableKontejner)
        self.splitter0.addWidget(self.satniTableKontejner)
        # splitter1 je horizontalni split izmedju tablice sa podacima i splitter2
        self.splitter1.addWidget(self.splitter0)
        self.splitter1.addWidget(self.splitter2)
        # splitter2 je vertikalni split izmedju plot toolbara, plota, i splitter3
        self.splitter2.addWidget(self.combinedNavigationUnit)
        self.splitter2.addWidget(self.kanvas)
        self.splitter2.addWidget(self.splitter3)
        # splitter3 je horizontalni split izmedju tablice sa korekcijama i statistike
        #self.splitter3.addWidget(self.correctionTabWidget)
        #self.splitter3.addWidget(self.statisticsTableView)
        # labeling change
        self.splitter3.addWidget(self.korrTableKontejner)
        self.splitter3.addWidget(self.statTableKontejner)

        # sve stavljamo u horizontalni layout i postavljamo u widget
        self.glavniLayout = QtWidgets.QHBoxLayout()
        self.glavniLayout.addWidget(self.splitter1)
        self.setLayout(self.glavniLayout)
        # POVEZIVANJE AKCIJA ELEMENATA SA FUNKCIJAMA
        # moramo uskladiti promjene aktivnog taba - kada promjenimo jedan, drugi bi se trebali uskladiti
        self.concentrationTabWidget.currentChanged.connect(self.sync_tabs)
        self.correctionTabWidget.currentChanged.connect(self.sync_tabs)
        self.concentrationSatniTabWidget.currentChanged.connect(self.sync_tabs)
        # navigacijski toolbar signalizira kada se koriste alati PAN i ZOOM
        self.plotNavigation.signal_tools_in_use.connect(self.kanvas.nav_tools_in_use)
        # graf signalizira izbor vremena sa grafa - potrebno je urediti zoom na tablice
        self.kanvas.signal_time_pick.connect(self.sync_kanvas_time_select)
        # graf signalizira zahtjev za promjenom flaga podataka
        self.kanvas.signal_flag_change.connect(self.odradi_promjenu_flaga)
        # promjena mjerne jedinice
        self.radioUGM3.clicked.connect(self.naredba_za_promjenu_mjerne_jedinice)
        self.radioPPB.clicked.connect(self.naredba_za_promjenu_mjerne_jedinice)

    def naredba_za_promjenu_mjerne_jedinice(self):
        """
        Funkcija služi kao callback prilikom promjene aktivnog radio gumba
        koji definira u kojim se mjernim jedinicama prikazuju rezultati.
        """
        # ako je origin signala ...
        if self.sender() == self.radioUGM3:
            self.AKTIVNE_JEDINICE = 'ug/m3'
            if self.session is not None:
                self.promjeni_mjerne_jedinice(ppx=False)
        elif self.sender() == self.radioPPB:
            self.AKTIVNE_JEDINICE = 'ppb'
            if self.session is not None:
                self.promjeni_mjerne_jedinice(ppx=True)
        else:
            raise ValueError('Krivi tip mjernih jedinica.')

    def postavi_mjerne_jedinice_bez_promjene(self, x):
        """
        Funkcija mjenja koji je od 2 radio gumba za promjenu jedinice aktivan bez
        da signalizira promjenu.

        Potrebno je zbog načina na koji se postavlja session u Display. Session može
        biti učitan sa RESTA (sve je tada u ug/m3) ili iz nekog spremljenog sessiona
        (mjerene jedinice mogu biti ili ppb ili ug/m3). Način za čuvanje konzistencije
        je manualno prebacivanje aktivnog radio gumba na ug/m3 i forsiranje promjene u ug/m3
        za session. Ova funkcija samo prebacuje radio gumb.
        """
        #block signale
        self.radioPPB.blockSignals(True)
        self.radioUGM3.blockSignals(True)
        if 'pp' in x:
            self.radioPPB.setChecked(True)
            self.radioUGM3.setChecked(False)
            self.AKTIVNE_JEDINICE = 'ppb'
        else:
            self.radioPPB.setChecked(False)
            self.radioUGM3.setChecked(True)
            self.AKTIVNE_JEDINICE = 'ug/m3'
        #unblock signale
        self.radioPPB.blockSignals(False)
        self.radioUGM3.blockSignals(False)

    def set_session(self, x):
        """
        Funkcija zadužena za postavaljanje novog Session objekta. Bilo da učitavamo podatke
        sa REST-a ili iz filea, uvijek se stvara novi Session koji drži sve potrebne podatke
        za prikaz i rad sa podacima. Ova funkcija pokreće primarni update kontrolnog sučelja.
        Između ostalog, moramo stvoriti tabove, tablice, povezati elemente ...

        #set session je bitan.. ako se podaci učitavaju sa REST ili iz filea moramo se
        pobrinuti da su mjerne jedinice u redu. REST je masenim koncentracijama, dok ucitani
        file može biti u svemu. Možda nije pametno, ali forsiramo jedinice u ug/m3.
        """
        # zapamti referencu na session
        self.session = x
        # izbrisi stare tablice iz tabova, napravi i povezi nove
        self.generiraj_nove_tabove()
        # spoji modele iz Sessiona sa gui-djelovima displaya
        self.connect_models()
        # postavi aktivni kanal u kanvas, bez crtanja
        aktivni_kanal = self.concentrationTabWidget.currentWidget().model().kanalId
        self.kanvas.promjeni_aktivni_kanal(aktivni_kanal, draw=False)
        # prosljedi instancu dokumenta kanvasu...ovo će pokrenuti crtanje
        self.kanvas.set_session(self.session)
        # moramo se pobrinuti za mjerne jedinice prilikom loada - force nazad u ug/m3
        self.postavi_mjerne_jedinice_bez_promjene('ug/m3')
        self.promjeni_mjerne_jedinice(ppx=False)

    def promjeni_mjerne_jedinice(self, ppx=True):
        """
        funkcija mjenja mjerne jedinice iz ppb u ug/m3 i obrnuto. Ako je "ppx" True pretvaramo
        u ppb ili ppm. Inače pretvaramo u ug/m3 ili mg/m3.

        - Svaki pojedini kanal mora promjeniti jedinice i metapodatke.
        - Ako je kanal iz PM grupe ne pretvaramo -> mora ostati u ug/m3
        - Moramo ponovno primjeniti korekciju
            - promjena mjenja samo koncentracije - korekcija se računa na ispravan način primjenom
        """
        #TODO! primarni problem... convert units moram signalizirati promjenu svih tablica naknadno da se updateaju.
        #TODO! headeri tablica se moraju syncati na pametan način...
        for kanal in self.session.sviKanali:
            datastore = self.session.get_datastore(kanal)
            if datastore.isPM:
                #PM nema smislenu konverziju u ppb format - mora ostati u ug/m3
                pass
            else:
                # pokreni promjenu jedinica za svaki model
                datastore.korekcija.convert_units(ppx=ppx) #korekcija ide prva...
                datastore.koncentracija.convert_units(ppx=ppx)
                datastore.satni.convert_units(ppx=ppx)
                datastore.zero.convert_units(ppx=ppx)
                datastore.span.convert_units(ppx=ppx)
                # convert units ne mjenja metapodatke... moramo promjeniti metapodatke
                # tj. mjernu jedinicu datastore-a
                # problem nastaje jer ako convert_units mjenja metapodatke sam, samo jedan dio datastorea dobije promjenu, dok ostali misle da su OK.
                # dakle... manualno mjenjanje metapodataka za svaki kanal.
                if ppx and (datastore.jedinica in ['ug/m3', 'mg/m3']):
                    # PRETVARANJE U ppb ili ppm
                    if datastore.jedinica == 'ug/m3':
                        datastore.jedinica = 'ppb'
                    else:
                        datastore.jedinica = 'ppm'
                elif (not ppx) and (datastore.jedinica not in ['ug/m3', 'mg/m3']):
                    # PRETVARANJE U ug/m3 ili mg/m3
                    if datastore.jedinica == 'ppb':
                        datastore.jedinica = 'ug/m3'
                    else:
                        datastore.jedinica = 'mg/m3'
                else:
                    # nema potrebe za konverzijom (vec smo u dobrom sustavu)
                    pass
        # primjena korekcije će se pobrinuti za računanje 'korekcija' i satno agregiranih u novim jedinicama
        self.primjeni_korekciju()

    def generiraj_nove_tabove(self):
        """
        Funkcija briše postojeće tabove, stvara nove te slaže odgovarajuće
        tablice tamo gdje pripadaju.
        """
        # blokiramo sve signale ,radi izbjegavanja nepotrebnih updateova
        self.concentrationTabWidget.blockSignals(True)
        self.correctionTabWidget.blockSignals(True)
        self.concentrationSatniTabWidget.blockSignals(True)
        self.statisticsTableView.blockSignals(True)
        # izbrisi postojece tabove iz TabWidgeta
        self.concentrationTabWidget.clear()
        self.concentrationSatniTabWidget.clear()
        self.correctionTabWidget.clear()
        # stari displayevi za tablice su i memoriji... trebaju se izbrisati da se izbjegne zabuna sa novim
        self.concentrationTableViews.clear()
        self.concentrationSatniTableViews.clear()
        self.correctionTableViews.clear()
        # generiramo nove tablice za prikaz podataka i spremamo ih na pripremljena mjesta
        for kanal in self.session.sviKanali:
            tabname = self.session.get_datastore(kanal).opis # naziv taba odgovara opisu
            # za svaki kanalId definiramo tablice za koncentraciju, satne i korekcijske parametre
            self.concentrationTableViews[kanal] = ConcentrationsTableView()
            self.concentrationSatniTableViews[kanal] = ConcentrationsSatniTableView()
            #NO2 ima posebnu tablicu korekcije
            if 'NO2' in tabname:
                self.correctionTableViews[kanal] = CorrectionsTableViewNO2()
            else:
                self.correctionTableViews[kanal] = CorrectionsTableView()
            # insert tablica u tab widgete
            indeks = self.concentrationTabWidget.addTab(self.concentrationTableViews[kanal], tabname)
            indeks = self.concentrationSatniTabWidget.addTab(self.concentrationSatniTableViews[kanal], tabname)
            indeks = self.correctionTabWidget.addTab(self.correctionTableViews[kanal], tabname)
        #moramo odblokirati signale da vratimo funkcionalnost
        self.concentrationTabWidget.blockSignals(False)
        self.correctionTabWidget.blockSignals(False)
        self.concentrationSatniTabWidget.blockSignals(False)
        self.statisticsTableView.blockSignals(False)

    def connect_models(self):
        """
        Povezivanje view-ova i modela u operativnu cjelinu
        """
        # povezivanje koncentracijskih tablica sa akcijama
        for tablica in self.concentrationTableViews.values():
            # izbor ljevim klikom - sve tablice moraju imati usklađen izbor
            tablica.clicked.connect(self.sync_koncentracija_table_selection)
            # desni klik poziva kontekstni menu za promjenu flaga na izabranim redovima
            tablica.signal_flag_change.connect(self.odradi_promjenu_flaga)
        # povezivanje satno agregiranih tablica sa akcijama
        for tablica in self.concentrationSatniTableViews.values():
            # izbor ljevim klikom - sve tablice moraju imati usklađen izbor
            tablica.clicked.connect(self.sync_satni_table_selection)
            # desni klik poziva kontekstni menu za promjenu flaga na izabranim redovima
            tablica.signal_flag_change.connect(self.odradi_promjenu_flaga)
        # link pojedinih modela iz sessiona sa tablicama
        for kanal in self.session.sviKanali:
            # postavljanje koncentracijskog modela
            self.concentrationTableViews[kanal].setModel(self.session.get_datastore(kanal).koncentracija)
            # postavljanje satnog modela
            self.concentrationSatniTableViews[kanal].setModel(self.session.get_datastore(kanal).satni)
            # postavljanje korekcijskog modela
            self.correctionTableViews[kanal].setModel(self.session.get_datastore(kanal).korekcija)
            # korekcijska tablica je specifična, moramo srediti trajne delegate za zadnja 2 reda (pretvoriti ih u gumbe)
            # iako NO2 ima posebnu tablicu i model, u biti sve funkcije imaju isti naziv, te nema potrebe za posebnim kodom
            self.correctionTableViews[kanal].sredi_delegate_za_tablicu()
            self.session.get_datastore(kanal).korekcija.update_persistent_delegates_korekcija.connect(self.correctionTableViews[kanal].sredi_delegate_za_tablicu)
            self.concentrationTableViews[kanal].update()
        # moramo prosljediti session statistickoj tablici
        self.statisticsTableModel.session = self.session

    def primjeni_korekciju(self):
        """
        Funkcija zadužena za primjenu korekcijskih parametara na podatke.
        #NO2 je special case - računa se iz NO i NOx u ppb
        """
        try:
            for grupa in self.session.get_grupirane_kanale():
                if len(grupa) > 1: #NOx ili PM slucaj
                    prvielement = list(grupa)[0] #grupa je set.. indeksiranje ne radi - konvert u listu
                    datastore0 = self.session.get_datastore(prvielement)
                    if datastore0.koncentracija.isNOx:
                        #NOx slučaj
                        kanalNO2 = None
                        noxppb = np.array([np.NaN])
                        noppb = np.array([np.NaN])
                        for kanal in grupa:
                            #iteracija po kanalima
                            datastore = self.session.get_datastore(kanal)
                            formula = datastore.koncentracija.formula
                            if formula == 'NOx':
                                korekcijskiFrejm = datastore.korekcija.dataframe #dataframe sa korekcijskim podacima
                                datastore.koncentracija.apply_correction(korekcijskiFrejm)
                                datastore.zero.apply_correction(korekcijskiFrejm)
                                datastore.span.apply_correction(korekcijskiFrejm)
                                noxppb = datastore.koncentracija.get_korekcija_in_ppb() #bitno za korekciju NO2
                            elif formula == 'NO':
                                korekcijskiFrejm = datastore.korekcija.dataframe #dataframe sa korekcijskim podacima
                                datastore.koncentracija.apply_correction(korekcijskiFrejm)
                                datastore.zero.apply_correction(korekcijskiFrejm)
                                datastore.span.apply_correction(korekcijskiFrejm)
                                noppb = datastore.koncentracija.get_korekcija_in_ppb() #bitno za korekciju NO2
                            else:
                                #za NO2 nas zanima kanal
                                kanalNO2 = kanal
                        # primjena na NO2 kanal tek nakon primjene na NOx i NO
                        datastore = self.session.get_datastore(kanalNO2)
                        korekcijskiFrejm = datastore.korekcija.dataframe #dataframe sa korekcijskim podacima
                        datastore.koncentracija.apply_correction(noxppb, noppb, korekcijskiFrejm) # primjena sa nox i no korektiranim podacima
                        datastore.zero.apply_correction(korekcijskiFrejm)
                        datastore.span.apply_correction(korekcijskiFrejm)
                    else:
                        #PM slučaj
                        for kanal in grupa:
                            datastore = self.session.get_datastore(kanal)
                            korekcijskiFrejm = datastore.korekcija.dataframe #dataframe sa korekcijskim podacima
                            datastore.koncentracija.apply_correction(korekcijskiFrejm)
                            datastore.zero.apply_correction(korekcijskiFrejm)
                            datastore.span.apply_correction(korekcijskiFrejm)
                else:
                    # single kanal case
                    kanal = list(grupa)[0]
                    datastore = self.session.get_datastore(kanal)
                    korekcijskiFrejm = datastore.korekcija.dataframe #dataframe sa korekcijskim podacima
                    datastore.koncentracija.apply_correction(korekcijskiFrejm)
                    datastore.zero.apply_correction(korekcijskiFrejm)
                    datastore.span.apply_correction(korekcijskiFrejm)

                # moramo uskladiti flagove na povezanim kanalima (logical i sync)
                self.sync_flagove_kod_povezanih_kanala()
                # reagregacija - ponovno postavljanje minutnih zapisa u satno agregirane
                self.reagregiraj_podatke()
                # naredba za ponovno crtanje, cuvaj prethodni zoom level sa noviSession=False
                self.kanvas.crtaj(noviSession=False)
                # refresh statistickih podataka
                self.statisticsTableModel.refresh()
        except AttributeError as err:
            logging.error(str(err), exc_info=True)
            reply = QtWidgets.QMessageBox.warning(
                self,
                'Upozorenje',
                'Podaci nisu ucitani.',
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Ok)
        except ValueError as err:
            logging.error(str(err), exc_info=True)
            reply = QtWidgets.QMessageBox.warning(
                self,
                'Upozorenje',
                'Podaci nisu dobro ispunjeni u tablici sa korekcijskim parametrima.',
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Ok)

    def odradi_promjenu_flaga(self, kanal, od, do, flag):
        """
        Funkcija mjenja vrijednost flaga za zadani kanal. "kanal" je integer ID programa mjerenja.
        "od", "do" su vremena u string formatu. "flag" je boolean (True ili False).
        Poziva se preko interakcije sa tablicama (koncentracija, satno agregirani) ili
        preko interakcije sa grafom. Ovo je glavni način na koji se mjenja flag u podacima.
        """
        # moramo pronaći povezane kanale od zadanog kanala (taj popis uključuje i zadani kanal)
        povezani = self.session.get_datastore(kanal).koncentracija.povezaniKanali
        # promjena flaga
        for k in povezani:
            self.session.get_datastore(k).koncentracija.change_user_flag(od, do, flag)
        # moramo uskladiti flagove na povezanim kanalima (logical i sync)
        self.sync_flagove_kod_povezanih_kanala()
        # reagregacija - ponovno postavljanje minutnih zapisa u satno agregirane
        self.reagregiraj_podatke()
        # naredba za ponovno crtanje, cuvaj prethodni zoom level sa noviSession=False
        self.kanvas.crtaj(noviSession=False)
        # refresh statistickih podataka
        self.statisticsTableModel.refresh()

    def sync_flagove_kod_povezanih_kanala(self):
        """
        Funkcija za usklađivanje flagova podataka. Problem nastaje jer moram ići kanal po kanal
        da nađem grupe koje moraju biti usklađene. Pronalaskom grupa moram preuzeti relevantne podatke
        iz grupe i urediti flagove tako da imaju logičkog smisla (npr. PM10 > PM1) i da su svi flagovi
        u skladu (npr. ako je PM1 negdje kriv, svi drugi PM-ovi moraju također biti proglašeni krivima).

        implementacija logike
        PM10 > PM2.5 > PM1
        NOx priblizno jednak (ne smije biti manji) od NO2 + NO (ppb slučaj)
        
        
        modifikacija
        1. moram izbaciti sve checkove osim LDL slučaja - dakle ne smije raditi logicki check za NOX i PM10
        """
        # step 1: moramo grupirati u nox ili PM
        # iteriramo kroz grupirane kanale
        for grupa in self.session.get_grupirane_kanale():
            # ako grupa ima jedan element - definitivno nije PM ili NOx
            # tj. nemamo posla, jer nemamo s čim usporediti kanal
            if len(grupa) > 1:
                #TODO! logički testovi kod podataka nisu potrebni - smatraj da je sve logički OK
#                # pronalazak tipa (NOx ili PM) i uređenog popisa kanala
#                tip, value_dict = self._test_for_nox_or_PM_and_order(grupa)
#                if tip == 'NOx':
#                    boolMask = self._logicki_check_mask_NOx(value_dict)
#                elif tip == 'PM':
#                    boolMask = self._logicki_check_mask_PM(value_dict)
#                else:
#                    # slučaj kada nešto ne valja -- vratimo sve True
#                    # ova linija u 99.99% slučaja neće biti izvršena
#                    boolMask = np.array([True])
                boolMask = np.array([True])
                # postavi logical flag u koncentracijski model svima u grupi
                for kanal in grupa:
                    self.session.get_datastore(kanal).koncentracija.set_logical_sync_flag(boolMask)
                # nakon postavljanja logickog flaga, bitno je uskladiti flagove u grupi
                outFlagovi = np.array([True])
                # kombiniraj sve flagove u grupi ...
                for kanal in grupa:
                    # flagovi su logical and stupca 'flag' i 'logical_flag'
                    flagovi = self.session.get_datastore(kanal).koncentracija.get_flags_to_sync()
                    # logical and između "flagovi" i "outputFlagovi" će vjerno napraviti kartu preklapanja
                    outFlagovi = np.logical_and(flagovi, outFlagovi)
                # kada imamo usklađeni flag moramo ga postaviti u modele koncentracije
                for kanal in grupa:
                    self.session.get_datastore(kanal).koncentracija.set_synced_flag(outFlagovi)

    def _test_for_nox_or_PM_and_order(self, grupa):
        """
        Funkcija koja za 'grupu' podataka (integeri kanalId) prepoznaje da li je NOx ili PM grupa
        te preslaguje kanale u dobar redosljed ([PM10, PM2.5, PM1] ili [NOx, NOx, NO]).

        Ako imamo slučaj da kanal nedostaje, NOx će napraviti error negdje dalje u nizu prilikom računanja
        korekcije (potrebni su NO i NOx za računanje NO2). PM slučaj se može provući i bez jednog od 2
        PM-a (slučaj sa 1 PM u biti nije grupa i neće pokrenuti ovu funkciju)
        """
        kanali = list(grupa)
        # potrebo je utvrditi da li je NOx ili PM grupa, - dohvati datastore prvog iz grupe
        datastore0 = self.session.get_datastore(kanali[0])
        if datastore0.koncentracija.isPM:
            # PM slučaj
            out = {}
            for kanal in grupa:
                datastore = self.session.get_datastore(kanal)
                formula = datastore.koncentracija.formula
                if formula in ['PM10', 'PM2.5', 'PM1']:
                    out[formula] = datastore.koncentracija.dataframe.loc[:,'korekcija'].values
                else:
                    # skoro nemoguć slučaj
                    raise ValueError('Pogrešni kanal u PM grupi - {0}'.format(str(kanal)))
            return 'PM', out
        elif datastore0.koncentracija.isNOx:
            # NOx slučaj
            out = {}
            for kanal in grupa:
                datastore = self.session.get_datastore(kanal)
                formula = datastore.koncentracija.formula
                if formula in ['NOx', 'NO', 'NO2']:
                    out[formula] = datastore.koncentracija.get_korekcija_in_ppb()
                else:
                    # skoro nemoguć slučaj
                    raise ValueError('Pogrešni kanal u PM grupi - {0}'.format(str(kanal)))
            return 'NOx', out
        else:
            # ako kanal nije povezan sa NOx ili PM grupom, vraćamo None i prazni dict
            # kao signal da ne trebamo uskladiti kanale.
            return None, {}

        #TODO! old code...
#        kanali = list(grupa)
#        # trebamo utvrditi da li je NOx ili PM grupa - dohvati datastore prvog iz grupe
#        datastore0 = self.session.get_datastore(kanali[0])
#        if datastore0.koncentracija.isPM:
#            # PM slučaj
#            sljed = ['pm10', 'pm25', 'pm1'] # tekst je placeholder
#            for kanal in grupa:
#                datastore = self.session.get_datastore(kanal) # moramo naći formulu pojedinog kanala iz grupe
#                formula = datastore.koncentracija.formula
#                # zamjena mjesta u tablici sa brojem kanala
#                if formula == 'PM10':
#                    sljed[0] = datastore.koncentracija.dataframe.loc[:,'korekcija'].values
#                elif formula == 'PM2.5':
#                    sljed[1] = datastore.koncentracija.dataframe.loc[:,'korekcija'].values
#                elif formula == 'PM1':
#                    sljed[2] = datastore.koncentracija.dataframe.loc[:,'korekcija'].values
#                else:
#                    # skoro nemoguć slučaj
#                    raise ValueError('Pogresni kanal u PM grupi - {0}'.format(str(kanal)))
#            return 'PM', sljed
#        elif datastore0.koncentracija.isNOx:
#            # NOx slučaj
#            sljed = ['nox', 'no2', 'no'] # tekst je placeholder
#            for kanal in grupa:
#                datastore = self.session.get_datastore(kanal) # moramo naći formulu pojedinog kanala iz grupe
#                formula = datastore.koncentracija.formula
#                # zamjena mjesta u tablici sa brojem kanala
#                if formula == 'NOx':
#                    sljed[0] = datastore.koncentracija.get_korekcija_in_ppb()
#                elif formula == 'NO2':
#                    sljed[1] = datastore.koncentracija.get_korekcija_in_ppb()
#                elif formula == 'NO':
#                    sljed[2] = datastore.koncentracija.get_korekcija_in_ppb()
#                else:
#                    # skoro nemoguć slučaj
#                    raise ValueError('Pogresni kanal u NOx grupi - {0}'.format(str(kanal)))
#            return 'NOx', sljed
#        else:
#            # ako kanal nije povezan sa NOx ili PM grupom, vračamo None i praznu listu kao
#            # signal da ne trebamo uskladiti kanale
#            return None, [] #tip, ordered list of data

#    def _logicki_check_mask(self, sortedList):
#        """
#        logicki test na 3 arraya vrijednosti korekcije NOx, NO2, NO
#        Neke vrijednosti možda nedostaju, missing vrijednosti su stringovi te ih
#        treba izbaciti iz liste.
#
#        logical and ovih kriterija je OK, sve ostalo je lose
#        vrati boolean masku
#        """
#        # potrebno je redefinirati logicki check...
#        #1. PM10 > PM2.5 > PM1 je definitvno
#        #2. no + no2 u ppb u mora biti manji od nox (uz neku manju toleranciju pogreške)
#
#        #sorted list mora izbaciti sve stringove s time da čuva redosljed od najvećeg do najmanjeg
#        sortedList2 = [i for i in sortedList if type(i)!=str]
#        with warnings.catch_warnings():
#            # suppress warnings in context manager (all NaN slice encountered ...)
#            # Problem nastaje kada dobijemo listu sa NaN podacima npr. NOx je negdje NaN gdje NO nije.
#            # Usporedbe tada javljaju warning koji je u prinicipu bespotreban jer output logicke usporedbe
#            # bilo čega sa NaN je False (što nama odgovara).
#            warnings.simplefilter("ignore")
#            out = np.array([True]) #definiramo output
#            # iteriramo u parovima - zato skraćujemo listu za 1, a znamo da lista u
#            # principu ima bar2 elementa jer bi inace test prije propao.
#            for i in range(len(sortedList2)-1):
#                val1 = sortedList2[i]
#                val2 = sortedList2[i+1]
#                tmp = val1 > val2
#                out = np.logical_and(out, tmp)
#            return out

    def _logicki_check_mask_NOx(self, mapa):
        """
        logicki test na 3 arraya vrijednosti korekcije NOx, NO2, NO

        logical and ovih kriterija je OK, sve ostalo je lose
        vrati boolean masku
        """
        #TODO! potrebno je definirati logicki check...
        #1. no + no2 (u ppb) mora biti manji od nox (uz neku manju toleranciju pogreške zbog zaokruživanja?)
        #2. no (u ppb) mora biti manji od nox
        #3. no2 (u ppb) mora biti manji od nox
        if len(mapa) != 3:
            # imamo problem jer neki kanal iz nox grupe nedostaje
            raise ValueError('Nepotpun broj kanala, potrebni su NOx, NO i NO2 kanali')

        with warnings.catch_warnings():
            # suppress warnings in context manager (all NaN slice encountered ...)
            # Problem nastaje kada dobijemo listu sa NaN podacima npr. NOx je negdje NaN gdje NO nije.
            # Usporedbe tada javljaju warning koji je u prinicipu bespotreban jer output logicke usporedbe
            # bilo čega sa NaN je False (što nama odgovara).
            warnings.simplefilter("ignore")
            out = np.array([True]) #definiramo output
            # provjera : zbroj NO i NO2 ne smije biti veći od NOx
            # implementacija blage tolerancije... 5% ukupne NOx koncentracije ??? 
            tolerancija = mapa['NOx']*0.05
            test1 = np.greater_equal(mapa['NOx']+tolerancija, mapa['NO'] + mapa['NO2'])
#            test1 = np.greater_equal(mapa['NOx'], mapa['NO'] + mapa['NO2'])
            # provjera : NO ne smije biti veći od NOx
            test2 = np.greater_equal(mapa['NOx'], mapa['NO'])
            # provjera : NO2 ne smije biti veći od NOx
            test3 = np.greater_equal(mapa['NOx'], mapa['NO2'])
            # logical and sva 3 outputa
            out = np.logical_and(test1, test2)
            out = np.logical_and(out, test3)
            return out          

    def _logicki_check_mask_PM(self, mapa):
        """
        logicki test na 3 arraya vrijednosti korekcije PM10, PM2.5, PM1

        logical and ovih kriterija je OK, sve ostalo je lose
        vrati boolean masku
        """
        #potrebno je definirati logicki check...???
        #1. PM10 > PM2.5 > PM1
        #potrebno je srediti listu arrayeva od najvećeg do najmanjeg
        sorted_list = []
        if 'PM10' in mapa.keys():
            sorted_list.append(mapa['PM10'])
        if 'PM2.5' in mapa.keys():
            sorted_list.append(mapa['PM2.5'])
        if 'PM1' in mapa.keys():
            sorted_list.append(mapa['PM1'])
        # u principu, imamo 4 slučaja:
        # 1. postaje PM10, PM2.5 i PM1 -- OK
        # 2. nedostaje jedan od PM-ova -- moguć slučaj (npr. nedostaje PM1), OK
        # 3. nedostaju dva PM-a -- nemoguće, tada ne postoji grupa
        # 4. nedostaju svi PM-ovi -- nemoguće, tada ne postoji grupa
        # dakle... imamo listu od 2 ili 3 elementa
        with warnings.catch_warnings():
            # suppress warnings in context manager (all NaN slice encountered ...)
            # Problem nastaje kada dobijemo listu sa NaN podacima npr. NOx je negdje NaN gdje NO nije.
            # Usporedbe tada javljaju warning koji je u prinicipu bespotreban jer output logicke usporedbe
            # bilo čega sa NaN je False (što nama odgovara).
            warnings.simplefilter("ignore")
            out = np.array([True]) #definiramo output
            # iteriramo u parovima - zato skraćujemo listu za 1, a znamo da lista u
            # principu ima bar2 elementa jer bi inace test prije propao.
            for i in range(len(sorted_list)-1):
                val1 = sorted_list[i]
                val2 = sorted_list[i+1]
                tmp = val1 > val2
                out = np.logical_and(out, tmp)
            return out

    def reagregiraj_podatke(self):
        """
        Funkcija za ponovnu agregacija podataka. Mehanizam ide preko ponovnog
        postavljanja minutnih koncentracija u satni model."""
        # za sve učitane kanale
        for kanal in self.session.sviKanali:
            # dohvati datastore
            datastore = self.session.get_datastore(kanal)
            # dohvati minutni frejm podataka
            minutniFrejm = datastore.koncentracija.dataframe
            # satni model automatksi agregira podatke
            datastore.satni.dataframe = minutniFrejm

    def sync_tabs(self, indeks):
        """
        Funkcija za usklađivanje izabranog taba. Cilj je sinkronizirati aktivni tab
        kroz sve tabWidgete tj. kada netko prebaci na kanal 'X', sve druge tablice
        trebaju se prebaciti na 'X'
        """
        # block signals - dok manipuliramo tabovima bolje je ugasiti sve signale
        self.concentrationTabWidget.blockSignals(True)
        self.correctionTabWidget.blockSignals(True)
        self.statisticsTableView.blockSignals(True)
        self.concentrationSatniTabWidget.blockSignals(True)
        # dohvati kanal - signal ima potpis pošiljatelja (tabwidget) čiji trenutni widget
        # odgovara tablici koja ima model u kojem je definiran kanalId
        kanal = self.sender().currentWidget().model().kanalId
        # moramo prebaciti koncentracijski tab
        i = self.concentrationTabWidget.indexOf(self.concentrationTableViews[kanal]) # pronađi indeks u tabu za kanal
        self.concentrationTabWidget.setCurrentIndex(i) # set pronadjenog indeksa
        # moramo prebaciti tab satno agregirane koncentracije
        i = self.concentrationSatniTabWidget.indexOf(self.concentrationSatniTableViews[kanal])
        self.concentrationSatniTabWidget.setCurrentIndex(i)
        # moramo prebaciti tab korekcije
        i = self.correctionTabWidget.indexOf(self.correctionTableViews[kanal])
        self.correctionTabWidget.setCurrentIndex(i)
        # unblock signals - zavrsili smo sa prebacivanjem tabova
        self.concentrationTabWidget.blockSignals(False)
        self.correctionTabWidget.blockSignals(False)
        self.statisticsTableView.blockSignals(False)
        self.concentrationSatniTabWidget.blockSignals(False)
        # promjena aktivne tablice mora promjeniti fokus crtanja
        # tj. kanvas mora dobiti informaciju koji je aktivni kanal
        self.kanvas.promjeni_aktivni_kanal(kanal)

    def sync_koncentracija_table_selection(self, modelindex):
        """
        Funkcija usklađuje izbor pojedinog reda u koncentracijskim tablicama.
        Tj. Izbor u jednoj tablici mora odgovarati drugim tablicama u drugim tabovima.
        Funkcija je callback za left click na tablicu sa koncentracjiama.
        """
        # iz widgeta pronaci aktivnu tablicu, tj. njen model
        modelAktivneTablice = self.concentrationTabWidget.currentWidget().model()
        # dohvati izabrani red aktivne tablice
        red = modelindex.row()
        # dohvati vrijeme pod redom
        tajm = modelAktivneTablice.get_index_for_row(red)
        # uskladi ostale tablice
        self.sync_kanvas_time_select(tajm)

    def sync_satni_table_selection(self, modelindex):
        """
        Funkcija usklađuje izbor pojedinog reda u satno agregiranim tablicama.
        Tj. Izbor u jednoj tablici mora odgovarati drugim tablicama u drugim tabovima.
        Funkcija je callback za left click na tablicu sa satno agregiranim podacima.
        """
        # iz widgeta pronaci aktivnu tablicu, tj. njen model
        modelAktivneTablice = self.concentrationSatniTabWidget.currentWidget().model()
        # dohvati izabrani red aktivne tablice
        red = modelindex.row()
        # dohvati vrijeme pod redom
        tajm = modelAktivneTablice.get_index_for_row(red)
        # uskladi ostale tablice
        self.sync_kanvas_time_select(tajm)

    def sync_kanvas_time_select(self, tajm):
        """
        Funkcija koja odrađuje izbor reda u tablicama. Za zadano vrijeme,
        tablice moraju izabrati najbliži red.

        trazenje najblizeg reda je u banani i traje... fora je da su tablice u
        vecini slucajeva jednako indeksirane... moram grupirati prema broj_u_satu
        """
        mapa = self._grupiraj_prema_broj_u_satu()
        for grupa in mapa.values():
            prvi = grupa[0] #prvi od kanala iz grupe
            # nalazimo najblizi red u tablici prvog kanala
            red = self.concentrationTableViews[prvi].model().get_nearest_row(tajm)
            # postavljamo sve tablice istog vremenskog koraka na isti red (bez pretrazivanja svake)
            for table in self.concentrationTableViews.values():
                table.selectRow(red)
            # nalzimo najblizi red u stanoj tablici prvog kanala
            red = self.concentrationSatniTableViews[prvi].model().get_nearest_row(tajm)
            # postavljamo sve satne tablice istog vremenskog koraka na isti red (bez pretrazivanja svake)
            for table in self.concentrationSatniTableViews.values():
                table.selectRow(red)

    def _grupiraj_prema_broj_u_satu(self):
        """Helper funkcija za grupiranje kanala prema broju podataka u satu.
        Ideja je napraviti shortcut prilikom izbora redka u tablici sa podacima
        nakon klika na grafu.

        Funkcija vraća mapu {broj_u_satu:[lista kanala]}
        """
        out = {}
        for kanal in self.session.sviKanali:
            broj_u_satu = self.session.get_datastore(kanal).koncentracija.broj_u_satu
            if broj_u_satu in out.keys():
                out[broj_u_satu].append(kanal)
            else:
                out[broj_u_satu] = [kanal]
        return out
