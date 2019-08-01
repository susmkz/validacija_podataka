#!/usr/bin/python3
# -*- coding: utf-8 -*-
import datetime
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui


class SatniTablica(QtCore.QAbstractTableModel):
    """
    Klasa za model podataka koncentracije (tablica)
    """
    def __init__(self):
        super(SatniTablica, self).__init__()
        # predvidjeni stupci u tablici sa podacima
        self._EXPECTED_COLUMNS = [
            'koncentracija', #vrijednost izmjerene koncentracije (float)
            'korekcija', #vrijednost korekcije (float)
            'flag', #FLAG - ispravnost podatka (boolean)
            'status', #status integer (integer)
            'obuhvat'] #obuhvat podataka (integer)
        # pandas DataFrame sa podacima (sa zadanim stupcima)
        self._DF = pd.DataFrame(columns=self._EXPECTED_COLUMNS)
        # kanal Id - ID programa mjerenja iz baze
        self._kanalId = None
        # broj podataka u satu (neki loggeri nemaju minutno uzorkovanje)
        self._broj_u_satu = None
        # mapa sa metapodacima kanala (formula, postaja, mjerna jedinica...)
        self._metaData = {}
        # mapa sa bit/status podacima (za binarno kodiranje/dekodiranje statusa)
        self._status_int2str = {}
        self._status_str2int = {}
        # lookup mapa za vec "prevedene" statuse
        self._status_lookup = {}

    ##################### QT MODEL FUNCTIONS - START ###########################
    def rowCount(self, parent=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Preko nje view dohvaća broj redova u tablici. Broj redova
        odgovara broju redova u frejmu sa podacima
        """
        return len(self._DF)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Preko nje view dohvaća broj stupaca u tablici.
        Prikazujemo samo 4 stupca zbog smanjivanja podataka na ekranu:
            stupac 0 --> koncentracija
            stupac 1 --> korekcija
            stupac 2 --> obuhvat
            stupac 3 --> opis statusa
        """
        return 4

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
        """
        # ako je indeks pogrešno zadan nemamo što raditi
        if not index.isValid():
            return None
        # dohvaćamo red i stupac indeksa
        row = index.row()
        col = index.column()
        # DISPLAY ROLE - sto prikazujemo u ćeliji
        if role == QtCore.Qt.DisplayRole:
            if col == 0:
                # za stupac 0, vraćamo stupac koncentracije u datafrejmu -> 0
                value = self._DF.iloc[row, 0]
                return str(round(value, 3))
            elif col == 1:
                # za stupac 1, vraćamo stupac korekcije u datafrejmu -> 1
                value = self._DF.iloc[row, 1]
                return str(round(value, 3))
            elif col == 2:
                # za stupac 2, vraćamo stupac obuhvat u datafrejmu -> 4
                value = self._DF.iloc[row, 4]
                return str(round(value, 3))  # obuhvat
            else:
                # preostali stupac 3, vraćamo status, adaptiran u string format
                value = self._DF.iloc[row, 3] # ovo je int status
                out = self.decode_status(value) # pretvaramo ga u string zapis
                return str(out)
        # BACKGROUND ROLE - boja pozadine ćelije
        if role == QtCore.Qt.BackgroundRole:
            # cilj je obojati pozadinu ćelije u crveno ako je flag los
            value = self._DF.iloc[row, 2] # lokacija stupca flag
            if not value :
                # los flag, vrati transparentnu crvenu boju
                return QtGui.QBrush(QtGui.QColor(255,0,0,80))
        # TOOLTIP ROLE - tooltip na mouseover ćelije
        if role == QtCore.Qt.ToolTipRole:
            if col in [0,1]:
                # za koncentraciju i korekciju vrati broj (bez zaokruživanja)
                value = self._DF.iloc[row, col]
                return str(value)
            elif col == 3:
                # status string
                value = self._DF.iloc[row, 3]
                out = self.decode_status(value)
                return str(out)
            else:
                # obuhvat (bez zaokruživanja)
                value = self._DF.iloc[row, 4]
                return str(value)

    def headerData(self, section, orientation, role):
        """
        BITNA QT FUNKCIJA. Preko nje view definira nazive redaka i stupaca u tablici.
        """
        if orientation == QtCore.Qt.Vertical:
            # za redove koristimo vremenski indeks datafrejma
            if role == QtCore.Qt.DisplayRole:
                return str(self._DF.index[section].strftime('%Y-%m-%d %H:%M:%S'))
        if orientation == QtCore.Qt.Horizontal:
            # za stupce koristimo predefinirane nazive
            if role == QtCore.Qt.DisplayRole:
                if section == 2:
                    return str(self._DF.columns[4])
                elif section == 3:
                    return str(self._DF.columns[section])
                else:
                    # samo trebam pripaziti na mjerne jedinice... ppb pisem kao ppbV (ppmV)
                    if self.jedinica.startswith('pp'):
                        return str(self._DF.columns[section]) + " [" + str(self.jedinica) + "V]"
                    else:
                        return str(self._DF.columns[section]) + " [" + str(self.jedinica) + "]"

    @property
    def dataframe(self):
        """Getter datafrejma sa podacima (kopije)"""
        return self._DF.copy()

    @dataframe.setter
    def dataframe(self, frejm):
        """
        Setter datafrejma sa podacima. Ulazni frejm je dataframe iz koncentracijskog
        modela (minutni podaci). Prilikom postavljanja podaci se agregiraju.
        """
        # poziv na agregiranje podataka
        self._DF = self._satni_agregator(frejm.copy())
        # notifikacija o promjeni podataka za sve view-ove koji su spojeni
        self.layoutChanged.emit()

    @property
    def kanalId(self):
        """Getter ID programa mjerenja (jedinstvena oznaka u bazi)."""
        return self._kanalId

    @kanalId.setter
    def kanalId(self, x):
        """Setter ID programa mjerenja (jedinstvena oznaka u bazi)."""
        self._kanalId = x

    @property
    def broj_u_satu(self):
        """Getter broja očekivanih podataka u satu (neka mjerenja nemaju minutno
        uzorkovanje)."""
        return self._broj_u_satu

    @broj_u_satu.setter
    def broj_u_satu(self, x):
        """Setter broja očekivanih podataka u satu (neka mjerenja nemaju minutno
        uzorkovanje)."""
        self._broj_u_satu = x

    @property
    def status_code(self):
        """Getter mape koja sadrzi podatke o kodiranju statusa (int -> str)."""
        return self._status_int2str

    @status_code.setter
    def status_code(self, mapa):
        """Setter mape koja sadrzi podatke o kodiranju statusa (int -> str).
        Prilikom postavljanja, generiramo i obrnutu mapu (str -> int)"""
        self._status_int2str = mapa
        self._status_str2int = dict(zip(mapa.values(), mapa.keys()))

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

    def get_nearest_row(self, x):
        """
        Funkcija vraća red koji odgovara indeksu koji je najbliži vremenu x (pandas
        timestamp). Funkcija je potrebna za usklađivanje povezanih tablica i za interakciju sa
        grafom.
        """
        # zaokružimo vrijeme na 1 sat
        tableTime = x.round('H')
        # pretvaranje indeksa datafrejma u listu
        indeksi = list(self._DF.index)
        try:
            # pretraživanje liste za zaokruženo vrijeme
            return indeksi.index(tableTime)
        except Exception:
            # moguci slučaj, vrijeme je izvan dosega tablice
            if tableTime <= indeksi[0]:
                # slucaj kada je vrijeme manje od najmanjeg vremena u tablici
                return 0
            else:
                # slucaj kada je vrijeme veće od najmanjeg vremena u tablici
                # pretpostavka da je onda veće od najvećeg (inace bi bila u dosegu tablice)
                return len(self._DF)

    def get_index_for_row(self, x):
        """
        Funkcija vraća indeks (timestamp) vremena u datafrejmu pod rednim brojem x.
        Funkcija je potrebna prilikom promjene flaga iz tablice (potrebna su nam vremena od-do).
        """
        return self._DF.index[x]

    def _satni_agregator(self, frejm):
        """
        Slaganje satno agragiranih vrijednosti iz ulaznog frejma (minutni)

        ulazni frejm mora imati datetime index i stupce:
        'koncentracija', 'korekcija', 'flag', 'logical_flag', 'sync_flag' i 'status'
        """
        # priprema outputa
        agregirani = pd.DataFrame()
        # agregacija statusa
        agStatusi = frejm['status'].resample('H', closed='right', label='right').apply(self._binor_statuse)
        agregirani['status'] = agStatusi
        # problem je da imam 3 flaga - kombinirani flag mora dalje - logical and
        f1 = frejm.loc[:, 'flag'].values
        f2 = frejm.loc[:, 'logical_flag'].values
        f3 = frejm.loc[:, 'sync_flag'].values
        finalFlag = np.logical_and(f1, f2)
        finalFlag = np.logical_and(finalFlag, f3)
        # vrijednosti koncentracije i korekcije za lose flagove mjenjamo sa np.NaN -> priprema za agregiranje
        frejm.loc[finalFlag == False, 'koncentracija'] = np.NaN
        frejm.loc[finalFlag == False, 'korekcija'] = np.NaN
        # agregiranje koncentracije
        agKonc = frejm['koncentracija'].resample('H', closed='right', label='right').apply(self._calc_mean)
        agregirani['koncentracija'] = agKonc
        # agregiranje korekcije
        agKore = frejm['korekcija'].resample('H', closed='right', label='right').apply(self._calc_mean)
        agregirani['korekcija'] = agKore
        # count podataka / obuhvat --> na korekciji
        agCount = frejm['korekcija'].resample('H', closed='right', label='right').apply(self._calc_obuhvat)
        agregirani['obuhvat'] = agCount
        # provjera obuhvata, obuhvat ne valja moram postaviti status 'OBUHVAT'
        statusObuhvat = (2**self._status_str2int['OBUHVAT'])
        losObuhvat = agregirani['obuhvat'] < 75 # kriterij je vise ili jednako 75% za OK obuhvat
        agregirani.loc[losObuhvat, 'status'] = [(int(i) | statusObuhvat) for i in agregirani.loc[losObuhvat, 'status']]
        # test valjanosti mora ici po statusima
        agregirani['flag'] = [self._calc_valjan(i) for i in agregirani['status']]
        # preslozi stupce u ocekivani redosljed
        agregirani = agregirani[self._EXPECTED_COLUMNS]
        return agregirani

    def convert_units(self, ppx=True):
        """
        Funkcija pretvara vrijednosti u drugi sustav ovisno o parametru "ppx".
        Ako je "ppx" True, pretvaram u ppb ili ppm. Ako je "ppx" False, pretvaram
        u ug/m3 ili mg/m3. Model zna u kojim je mjernim jedinicama (metapodaci)
        te nakon promjene mora promjeniti metapodatke da reflektira promjenu.

        P.S. promjena numeričkih vrijednosti nije potrebna. Prilikom primjene korekcije
        satni se postavljaju iz već konvertiranih minutnih vrijednosti. Jedino moramo
        pripaziti da mjerna jedinica u metapodacima bude dobro zamjenjena (po potrebi)

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

    def _binor_statuse(self, arraylike):
        """
        Pomoćna funkcija za agregiranje stautsa. Rezultat je binary OR svih statusa.
        """
        if len(arraylike) == 0:
            # nema podataka - naljepi status los obuhvat automatski
            statusObuhvat = self._status_str2int['OBUHVAT']
            return int(2**statusObuhvat)
        # inicialni build up kombinacije svih statusa
        result = 0 #int value
        for i in arraylike:
            try:
                # binary or radi samo na integerima -> dodavanje novih statusa
                result |= int(i)
            except ValueError:
                pass
        return result

    def _calc_mean(self, arraylike):
        """
        Pomoćna funkcija za agregiranje koncentracija (i korekcija).
        Rezultat je srednja vrijednost, s time da se NaN vrijednosti ignoriraju.
        """
        if len(arraylike) == 0:
            # slucaj kada nedostaju podaci
            return -9999 #XXX! nisam siguran cemu ovaj hardcode vrijednosti?
        if self._test_for_all_nan_range(arraylike):
            #slucaj kada su svi NaN
            return np.NaN
        return np.nanmean(arraylike)

    def _count_nan(self, arraylike):
        """
        Pomoćna funkcija za agregiranje. Rezultat je broj NaN vrijednosti u
        listi.
        """
        if len(arraylike) == 0:
            return np.NaN
        return np.sum(np.isnan(np.array(arraylike, dtype=np.float64)))

    def _calc_obuhvat(self, arraylike):
        """
        Pomoćna funkcija za agregiranje obuhvata. Rezultat je broj vrijednosti koje nisu
        NaN podjeljenje sa brojem očekivanih podataka * 100.
        """
        if len(arraylike) == 0:
            # ako nema podataka , obuhvat je 0
            return 0
        broj_ocekivanih = self.broj_u_satu
        broj_nanova = self._count_nan(arraylike)
        return 100 * ((broj_ocekivanih - broj_nanova) / broj_ocekivanih)

    def _calc_valjan(self, x):
        """
        Pomoćna funkcija za agregiranje flaga. Vrati True ako je status ispod praga
        tolerancije - limit je flag iznad "NEDOSTAJE" (obuhvat, satni errori, kontrola satni...).
        """
        nedostajeStatus = self._status_str2int['NEDOSTAJE']
        # binary OR svih statusa do i uključujući 'NEDOSTAJE' definitivno je manji
        # od idućeg statusa (SATNI_ERR1) dakle ako je status ispod idućeg, sve je OK.
        # P.S. status obuhvat je daleko veći i definitivno će triggerati False
        granica = int(2**(nedostajeStatus+1))
        if x < granica:
            return True
        else:
            return False

    def _test_for_all_nan_range(self, listlike):
        """
        Pomoćna funkcija koja provjerava da li su sve vrijednosti u nizu NaN, vraca True u slucaju
        prazne liste/arraya."""
        nnans = np.sum(np.isnan(np.array(listlike, dtype=np.float64)))
        if nnans == len(listlike):
            return True
        else:
            return False

    def get_valid_average(self):
        """
        Pomoćna funkcija za statistiku validiranih podataka. Srednja vrijednost
        dobro flagiranih.
        """
        nizOK = self._DF.loc[self._DF['flag'] == True]
        vals = nizOK['korekcija'].values
        if self._test_for_all_nan_range(vals):
            return np.NaN
        else:
            return np.nanmean(vals)

    def get_valid_std(self):
        """
        Pomoćna funkcija za statistiku validiranih podataka. Standardna devijacija
        dobro flagiranih.
        """
        nizOK = self._DF.loc[self._DF['flag'] == True]
        vals = nizOK['korekcija'].values
        if self._test_for_all_nan_range(vals):
            return np.NaN
        else:
            return np.nanstd(vals)

    def get_valid_min(self):
        """
        Pomoćna funkcija za statistiku validiranih podataka. Minimalna vrijednost
        dobro flagiranih.
        """
        nizOK = self._DF.loc[self._DF['flag'] == True]
        vals = nizOK['korekcija'].values
        if self._test_for_all_nan_range(vals):
            return np.NaN
        else:
            return np.nanmin(vals)

    def get_valid_max(self):
        """
        Pomoćna funkcija za statistiku validiranih podataka. Maksimalna vrijednost
        dobro flagiranih.
        """
        nizOK = self._DF.loc[self._DF['flag'] == True]
        vals = nizOK['korekcija'].values
        if self._test_for_all_nan_range(vals):
            return np.NaN
        else:
            return np.nanmax(vals)

    def get_valid_obuhvat(self):
        """
        Pomoćna funkcija za statistiku validiranih podataka. Ukupni obuhvat
        dobro flagiranih.
        """
        #broj podataka sa flag == True / broj podataka
        nizOK = len(self._DF.loc[self._DF['flag'] == True])
        svi = len(self._DF)
        if svi == 0:
            return 0.0
        else:
            return 100 * (nizOK / svi)
        
    def decode_status(self, x):
        """
        Funkcija dekodira status integer u string radi čitljivosti tablice.
        """
        # radi brzine, prvo provjerimo da li je status x već obrađen
        if x in self._status_lookup:
            return self._status_lookup[x]
        else:
            # slučaj ako prvi puta naletimo na status x
            out = [] #definiramo praznu listu za spremanje bit statusa
            for key, value in self._status_int2str.items():
                # ako je binary or između statusa i zadanog bita jednak statusu, to je
                # indikacija da je taj bit u statusu aktivan.
                if (int(x) | int(2**key)) == int(x):
                    out.append(value) # zapamtimo string zadanog status bita
            out = ", ".join(out) # pretvaranje liste u string
            self._status_lookup[x] = out # zapamti rezultat da izbjegnemo ponovno racunanje
            return out


    @property
    def badFlagIndex(self):
        """
        Pomoćni property. Vraća boolean masku gdje su flagovi False, tj. lokaciju
        loših indeksa
        """
        losiIndeksi = self._DF['flag'] == False
        return losiIndeksi

    @property
    def goodFlagIndex(self):
        """
        Pomoćni property. Vraća boolean masku gdje su flagovi True, tj. lokaciju
        dobrih indeksa
        """
        dobriIndeksi = self._DF['flag'] == True
        return dobriIndeksi

    @property
    def startTime(self):
        """
        Pomoćni property. Vrijeme prvog indeksa u datafrejmu. Potrebno za crtanje granica
        ucitanih podataka.
        """
        # ucitavamo dan po dan, ovo je samo Test da li imamo ucitanih podataka u frejmu
        if len(self._DF) > 2:
            # pomicemo vrijeme unazad 1 sat radi sinkronizacije sa Koncentracijskim podacima
            # rezultat je pridružen desno
            return self._DF.index[0] - datetime.timedelta(hours=1)
        else:
            return None

    @property
    def endTime(self):
        """
        Pomoćni property. Vrijeme zadnjeg indeksa u datafrejmu. Potrebno za crtanje granica
        ucitanih podataka.
        """
        # ucitavamo dan po dan, ovo je samo Test da li imamo ucitanih podataka u frejmu
        if len(self._DF) > 2:
            return self._DF.index[-1]
        else:
            return None

    @property
    def yPlotRange(self):
        """
        Pomoćni property. Raspon svih koncentracija i korekcija prosiren za 20%.
        Izlaz je tuple sa (min, max) vrijednosti.
        """
        if len(self._DF):
            tmp1 = self._DF['koncentracija'].values.copy() # koncentracije
            tmp2 = self._DF['korekcija'].values.copy() # korekcije
            test1 = self._test_for_all_nan_range(tmp1) # ispravnost koncentracija
            test2 = self._test_for_all_nan_range(tmp2) # ispravnost korekcija
            # granice koncentracije
            if test1:
                lowKonc = -1.0
                highKonc = 1.0
            else:
                lowKonc = np.nanmin(tmp1)
                highKonc = np.nanmax(tmp1)
            # granice korekcije
            if test2:
                lowKore = -1.0
                highKore = 1.0
            else:
                lowKore = np.nanmin(tmp2)
                highKore = np.nanmax(tmp2)
            # uzimamo manji od donjih granica i veci od gornjih granica
            od = np.min([lowKonc,lowKore])
            do = np.max([highKonc,highKore])
            #odmaknimo granice malo dalje od ruba za 10% raspona u svakom smjeru
            raspon = (do - od)*0.1
            return (od-raspon, do+raspon)
        else:
            # ako nemamo podataka vrati default raspon za graf
            return (-1.0, 1.0)

    @property
    def indeks(self):
        """
        Pomoćni property. Vraća potpuni indeks datafrejma (pandas timestampove).
        """
        return np.array(self._DF.index)

    @property
    def koncentracija_line(self):
        """
        Pomoćni property. Vraća niz vrijednosti koncentracije iz datafrejma.
        """
        return np.array(self._DF['koncentracija'].values)

    @property
    def korekcija_line(self):
        """
        Pomoćni property. Vraća niz vrijednosti korekcije iz datafrejma.
        """
        return np.array(self._DF['korekcija'].values)

    @property
    def koncentracijaOk(self):
        """
        Pomoćni property. Vraća niz vrijednosti koncentracije iz datafrejma, ali
        u redovima gdje je flag False, koncentracije mjenjamo sa NaN.
        """
        #boolean maska losih flagova
        losiIndeksi = self._DF['flag'] == False
        #vrijednosti
        out = self.koncentracija_line
        #pretvori lose flagove u NaN
        out[losiIndeksi] = np.NaN
        return out

    @property
    def koncentracijaBad(self):
        """
        Pomoćni property. Vraća niz vrijednosti koncentracije iz datafrejma, ali
        u redovima gdje je flag True, koncentracije mjenjamo sa NaN.
        """
        #boolean maska losih flagova
        dobriIndeksi = self._DF['flag'] == True
        #vrijednosti
        out = self.koncentracija_line
        #pretvori lose flagove u NaN
        out[dobriIndeksi] = np.NaN
        return out

    @property
    def korekcijaOk(self):
        """
        Pomoćni property. Vraća niz vrijednosti korekcije iz datafrejma, ali
        u redovima gdje je flag False, korekcije mjenjamo sa NaN.
        """
        #boolean maska losih flagova
        losiIndeksi = self._DF['flag'] == False
        #vrijednosti
        out = self.korekcija_line
        #pretvori lose flagove u NaN
        out[losiIndeksi] = np.NaN
        return out

    @property
    def korekcijaBad(self):
        """
        Pomoćni property. Vraća niz vrijednosti korekcije iz datafrejma, ali
        u redovima gdje je flag True, korekcije mjenjamo sa NaN.
        """
        #boolean maska losih flagova
        dobriIndeksi = self._DF['flag'] == True
        #vrijednosti
        out = self.korekcija_line
        #pretvori lose flagove u NaN
        out[dobriIndeksi] = np.NaN
        return out

    def get_pickle_map(self):
        """
        Funkcija za pomoć prilikom SAVE - LOAD operacija. Sprema sve bitne varijable
        u mapu.
        """
        mapa = {}
        # ne spremam dataframe jer se postavlja sa minutnim !
        mapa['kanalId'] = self.kanalId
        mapa['metaData'] = self.metaData
        mapa['status_code'] = self.status_code
        mapa['broj_u_satu'] = self.broj_u_satu
        return mapa

    def set_pickle_map(self, mapa):
        """
        Funkcija za pomoć prilikom SAVE - LOAD operacija. Iz mape preuzima vrijednosti
        koje postavlja u zadane varijable.
        """
        # ne učitavam dataframe jer se postavlja sa minutnim !
        self.kanalId = mapa['kanalId']
        self.metaData = mapa['metaData']
        self.status_code = mapa['status_code']
        self.broj_u_satu = mapa['broj_u_satu']
