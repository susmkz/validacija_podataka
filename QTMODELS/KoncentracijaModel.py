#!/usr/bin/python3
# -*- coding: utf-8 -*-
import copy
import warnings
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui


class KoncentracijaTablica(QtCore.QAbstractTableModel):
    """
    Klasa za model podataka koncentracije (tablica)
    """
    def __init__(self):
        """Konstruktor klase."""
        super(KoncentracijaTablica, self).__init__()
        # predvidjeni stupci u tablici sa podacima
        self._EXPECTED_COLUMNS = [
            'koncentracija', # vrijednost izmjerene koncentracije (float)
            'korekcija', # vrijednost korekcije (float)
            'flag', # FLAG - ispravnost podatka (boolean)
            'status', # status integer (integer)
            'id', # ID podatka u bazi (integer)
            'A', # parametar A korekcije (float za svaki vremenski indeks - varira u vremenu)
            'B', # parametar B korekcije (float za svaki vremenski indeks - varira u vremenu)
            'Sr', # parametar Sr korekcije (float za svaki vremenski indeks - varira u vremenu)
            'LDL', # Low Detection Limit (float za svaki vremenski indeks - varira u vremenu)
            'logical_flag', # flag koji prati status povezanih kanala - LOGICKI TEST npr. PM10 < PM1 = False
            'sync_flag'] # flag koji prati status povezanih kanala - SYNC TEST - ako je flag nedgje los, mora biti i u svim povezanim kanalima
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

    def rowCount(self, parent=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Preko nje view dohvaća broj redova u tablici. Broj redova
        odgovara broju redova u frejmu sa podacima
        """
        return len(self._DF)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """
        BITNA QT FUNKCIJA. Preko nje view dohvaća broj stupaca u tablici.
        Prikazujemo samo 3 stupca zbog smanjivanja podataka na ekranu:
            stupac 0 --> koncentracija
            stupac 1 --> korekcija
            stupac 2 --> opis statusa
        """
        return 3

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
            else:
                # za stupac 1, trebamo vratiti string opis statusa.
                value = self._DF.iloc[row, 3] # ovo je int status
                out = self.decode_status(value) # pretvaramo ga u string zapis
                return str(out)
        # BACKGROUND ROLE - boja pozadine ćelije
        if role == QtCore.Qt.BackgroundRole:
            # cilj je obojati pozadinu ćelije u crveno ako je flag los
            # moramo kombinirati 3 flaga - user, sync (ako povezani kanali nisu usklađeni), logical (logicki test na povezanim kanalima)
            f_logical = copy.copy(self._DF.iloc[row, 9]) # logical flag
            f_sync = copy.copy(self._DF.iloc[row, 10]) # sync flag
            f = copy.copy(self._DF.iloc[row, 2]) # flag
            # logical and svih kriterija
            if isinstance(f_sync, bool):
                f = f and f_sync
            if isinstance(f_logical, bool):
                f = f and f_logical
            if not f :
                # los flag, vrati transparentnu crvenu boju
                return QtGui.QBrush(QtGui.QColor(255,0,0,80))
        # TOOLTIP ROLE - tooltip na mouseover ćelije
        if role == QtCore.Qt.ToolTipRole:
            if col in [0,1]:
                # za koncentraciju i korekciju vrati broj (bez zaokruzivanja)
                value = self._DF.iloc[row, col]
                return str(value)
            else:
                # status string je identican display opciji
                value = self._DF.iloc[row, 3]
                out = self.decode_status(value)
                return str(out)

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
                    # stupac 2 je status --> stupac 3 u datafrejmu
                    return str(self._DF.columns[3])
                else:
                    # stupac 1 i 2 su identicni kao u datafrejmu (koncentracija / korekcija)
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
        """Setter datafrejma sa podacima."""
        self._DF = frejm.copy()
        # preslagujemo stupce u odgovarajuci redosljed
        self._DF = self._DF[self._EXPECTED_COLUMNS]
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
        # moramo izracunati period na koji zaokružujemo
        tmin = str(int(60 / self.broj_u_satu))
        res = "{0}Min".format(tmin)
        # zaokružimo vrijeme na odgovarajuću rezoluciju
        tableTime = x.round(res)
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

    def _test_ispravnosti_korekcijske_tablice(self, korekcijskiFrejm):
        """
        Funkcija služi za provjeru svih potrebnih podataka u tablici korekcijskih
        parametara.
        """
        df = korekcijskiFrejm.copy()
        # inicijalni broj redova tablice
        LEN1  = len(df)
        # test za praznu tablicu
        if LEN1 == 0:
            #tablica je prazna
            return None #signal da napravimo fake tablicu sa nan vrijednostima
        # pobrini se da su A, B, Sr float vrijednosti zbog racunanja
        df['A'] = df['A'].astype(float)
        df['B'] = df['B'].astype(float)
        df['Sr'] = df['Sr'].astype(float)
        # drop svih redova gdje imamo NaN vrijednosti
        df.dropna(axis=0, inplace=True)
        # korekcijska tablica ima stupac 'vrijeme', moramo ga prebaciti u indeks
        df = df.set_index(df['vrijeme'])
        df.drop('vrijeme', axis=1, inplace=True)
        # broj redova tablice sa izbacenim redovima sa NaN vrijednostima
        LEN2  = len(df)
        if LEN1 != LEN2:
            # ako LEN1 nije jednak LEN2 znaci da smo izbacili neki red - tablica nije dobro ispunjena
            raise ValueError('Parametri korekcije nisu dobro ispunjeni.')
        return df

    def _pripremi_korekcijsku_tablicu(self, korekcijskiFrejm):
        """
        Funkcija služi za pripremu i provjeru svih potrebnih podataka u tablici korekcijskih
        parametara.
        """
        # provjera da li je tablica dobro ispunjena
        df = self._test_ispravnosti_korekcijske_tablice(korekcijskiFrejm)
        if df is None:
            #imamo praznu tablicu, fake output sa NaN vrijednostima
            out = pd.DataFrame(
                data={'A':np.NaN, 'B':np.NaN, 'Sr':np.NaN},
                columns=['A','B','Sr'],
                index=self._DF.index)
            # return all NaN table
            return out
        # u principu podatak o korekciji je sa vremenskim indeksom manjim od ucitanih podataka
        # potrebno je prosiriti kraj tablice korekcije za zadnjom vrijednosti
        zadnjiIndeksKorekcije = df.index[-1]
        zadnjiIndeksPodataka = self._DF.index[-1]
        if zadnjiIndeksKorekcije < zadnjiIndeksPodataka:
            #extend zadnje vrijednosti u tablici korekcije do kraja podataka
            df.loc[zadnjiIndeksPodataka, 'A'] = df.loc[zadnjiIndeksKorekcije, 'A']
            df.loc[zadnjiIndeksPodataka, 'B'] = df.loc[zadnjiIndeksKorekcije, 'B']
            df.loc[zadnjiIndeksPodataka, 'Sr'] = df.loc[zadnjiIndeksKorekcije, 'Sr']
        # interpolacija na minutnu razinu
        if self.isPM:
            # PM imaju "step" tip korekcije
            df = df.resample('Min').ffill()
        else:
            # ostali imaju "linearni" tip korekcije
            df = df.resample('Min').interpolate()
        # reindex df radi preklapanja sa self._DF indeksima
        df = df.reindex(self._DF.index)
        return df

    def _calc_ldl_values(self, df):
        """racunanje ldl vrijednosti za frejm korekcije"""
        sr = df['Sr']
        A = df['A']
        ldl = (-3.3 * sr) / A
        df['LDL'] = ldl
        return df

    def _modify_LDL_status_and_flags(self):
        """
        Za svaki red u datafrejmu gdje je korekcija ispod LDL vrijednosti flag se
        mora postaviti na False. Također status tog reda treba dobiti LDL flag.
        U redovima gdje je korekcija iznad LDL ako postoji LDL status, on se mora maknuti.
        Problem nastaje sa modificiranjem Flaga - logika je u komentarima.
        """
        # potreban nam je int koji definira LDL status (2 na potenciju rednog broja statusa)
        ldlStatus = np.array(int(2**self._status_str2int['LDL'])).astype(np.int64)
        # krenimo sve is pocetka - makni sve LDL statuse iz podataka
        statusi = self._DF.loc[:,'status'].values.astype(np.int64)
        # brisanje status flaga (ovo je u biti primjena binarnih operatora na integere)
        statusiBezLDL = statusi & (~ ldlStatus)
        self._DF.loc[:,'status'] = statusiBezLDL
        # svi podaci ciji je jedini offense bio LDL flag i dalje su False moraju biti prebaceni na True
        nemaNekiStatus = statusiBezLDL == 0 # True tamo gdje ne postoji status nakon sto je LDL maknut
        flagoviFalse = self._DF.loc[:,'flag'] == False # True tamo gdje je flag False
        zaPrebacitiFlag = np.logical_and(nemaNekiStatus, flagoviFalse) # bool maska tamo gdje nema statusa a flag je false
        # prebaciti flagove u True koji su bili False samo zbog LDL statusa
        self._DF.loc[zaPrebacitiFlag, 'flag'] = True
        # stavljanje novih LDL flagova ...
        # lokacijija svih ispod LDL
        losiLDL = self.badLDLIndex
        # promjena -- dodavanje LDL na status
        noviStatusi = self._DF.loc[losiLDL, 'status'].values.astype(np.int64)
        noviStatusi = noviStatusi | ldlStatus # dodavanje status flaga (binary OR)
        self._DF.loc[losiLDL, 'status'] = noviStatusi
        # promjeni i flag
        self._DF.loc[losiLDL, 'flag'] = False

    def convert_units(self, ppx=True):
        """
        Funkcija pretvara vrijednosti u drugi sustav ovisno o parametru "ppx".
        Ako je "ppx" True, pretvaram u ppb ili ppm. Ako je "ppx" False, pretvaram
        u ug/m3 ili mg/m3. Model zna u kojim je mjernim jedinicama (metapodaci)
        te nakon promjene mora promjeniti metapodatke da reflektira promjenu.

        P.S. mjenjamo samo 'koncentraciju' - ostale vrijednosti se prevaraju
        tjekom primjene korekcije.
        
        ispravak...
        promjenu metapodataka o jedinici ostavljamo funkciji koja zove ovu funkciju
        """
        if ppx and (self.jedinica not in ['ppb', 'ppm']):
            # PRETVARANJE U PPx (PPB ili PPM)
            # dohvati koncentraciju
            currentVals = self._DF.loc[:,'koncentracija'].values
            # primjeni konverziju u ppm ili ppb
            newVals = currentVals / self.unitConversionFactor
            # postavi nove vrijednosti
            self._DF.loc[:,'koncentracija'] = newVals
            # postavi nove jedinice u metapodatke
#            if self.jedinica == 'ug/m3':
#                self.jedinica = 'ppb'
#            else:
#                self.jedinica = 'ppm'
        elif (not ppx) and (self.jedinica not in ['ug/m3', 'mg/m3']):
            # PRETVARANJE U ug/m3 ili mg/m3
            # dohvati koncentraciju
            currentVals = self._DF.loc[:,'koncentracija'].values
            # primjeni konverziju u ug/m3 ili mg/m3
            newVals = currentVals * self.unitConversionFactor
            # postavi nove vrijednosti
            self._DF.loc[:,'koncentracija'] = newVals
            # postavi nove jedinice u metapodatke
#            if self.jedinica == 'ppb':
#                self.jedinica = 'ug/m3'
#            else:
#                self.jedinica = 'mg/m3'
        else:
            # nema potrebe za konverzijom (vec smo u dobrom sustavu)
            pass
        # singnal da je došlo do promjene u tablici
        self.layoutChanged.emit()

    def apply_correction(self, correctFrame):
        """
        Funkcija služi za primjenu korekcije na ucitane podatke o koncentraciji. Ulazni
        parametar correctFrame je dataframe sa podacima sa A, B, Sr za zadani kanal.

        Koristimo linearnu korekciju --> korekcija = A * koncentracija + B

        Prilikom korekcije također se računa LDL vrijednost te se radi provjera da li
        su korigirani podaci iznad LDL (modifikacija flaga i statusa po potrebi).
        """
        df = correctFrame.copy()
        # priprema tablice korekcijskih parametara za rad sa podacima
        # -> inicijalni test, interpolacija, podesavanje indeksa sa glavnom tablicom
        df = self._pripremi_korekcijsku_tablicu(df)
        # racunanje ldl vrijednosi
        df = self._calc_ldl_values(df)
        # kopiranje vrijednosi A, B, Sr, LDL, u glavnu tablicu
        self._DF.loc[:,'A'] = df['A']
        self._DF.loc[:,'B'] = df['B']
        self._DF.loc[:,'Sr'] = df['Sr']
        self._DF.loc[:,'LDL'] = df['LDL']
        # racunanje korekcije
        korekcija = self._DF.loc[:,'koncentracija'].values * self._DF.loc[:,'A'].values + self._DF.loc[:,'B'].values
        self._DF.loc[:,'korekcija'] = korekcija
        # potrebno je prilagoditi flagove i statuse za slucaj kada je korekcija ispod LDL-a
        self._modify_LDL_status_and_flags()

    def change_user_flag(self, od, do, value):
        """
        Funkcija služi promjeni flaga od strane korisnika unutar granica od - do (pandas
        timestampovi) u novu vrijednost (True ili False).

        Uz flag moramo promjeniti i status te provjeriti da je LDL kriterij i dalje OK.
        """
        # status za kontrolu
        statusKontrola = np.array(int(2**self._status_str2int['KONTROLA'])).astype(np.int64)
        # promjena flaga
        self._DF.loc[od:do, 'flag'] = value
        # promjena stautsa
        statusiZaPromjenu = self._DF.loc[od:do, 'status'].values.astype(np.int64)
        if value:
            # ako je True, moramo maknuti status bit kontrole
            statusiZaPromjenu = statusiZaPromjenu & (~ statusKontrola)
        else:
            # ako je True, moramo postaviti status bit kontrole
            statusiZaPromjenu = statusiZaPromjenu | statusKontrola
        # postavljanje izmjenjenih statusa
        self._DF.loc[od:do, 'status'] = statusiZaPromjenu
        # TEST ZA LDL VIOLATION LDL nikada ne smijemo prebaciti u True
        self._modify_LDL_status_and_flags()

    def get_flags_to_sync(self):
        """
        Funkcija vraća logicki and kopije stupca 'flag' i 'logical_flag' za usklađivanje.
        Bitno za povezane kanale.
        """
        f1 = self._DF.loc[:,'flag'].values.copy()
        f2 = self._DF.loc[:,'logical_flag'].values.copy()
        return np.logical_and(f1, f2)

    def get_flags(self):
        """
        Funkcija dohvaća kombinirani flag (logical and) svih flagova (flag, logical_flag,
        sync_flag).
        """
        out = self.get_flags_to_sync()
        f3 = self._DF.loc[:,'sync_flag'].values.copy()
        out = np.logical_and(out, f3)
        return out

    def set_synced_flag(self, flags):
        """
        Postavljanje usklađenog flaga u stupac sync_flag : prati razlike gdje
        se flagovi razlikuju u povezanim kanalima.
        -flags: np.array boolean vrijednosti cijelog niza
        """
        i = flags.copy()
        self._DF.loc[:,'sync_flag'] = i
        # notifikacija o promjeni podataka za sve view-ove koji su spojeni
        self.layoutChanged.emit()

    def set_logical_sync_flag(self, flags):
        """
        Postavljanje logičkog flaga u stupac 'logical_flag' : prati gdje je
        narušen logički integritet povezanih kanala (npr. PM10 < PM1).
        Ulaz je bool maska (numpy array)
        """
        i = flags.copy()
        self._DF.loc[:, 'logical_flag'] = i
        # notifikacija o promjeni podataka za sve view-ove koji su spojeni
        self.layoutChanged.emit()

    def _test_for_all_nan_range(self, listlike):
        """
        Pomoćna funkcija koja provjerava da li su sve vrijednosti u nizu NaN, vraca True u slucaju
        prazne liste/arraya."""
        nnans = np.sum(np.isnan(np.array(listlike, dtype=np.float64)))
        if nnans == len(listlike):
            return True
        else:
            return False

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

    #TODO! problem sa originalnim crtanjem flagova...fora je bez korekcije sync i logical su False pa sve ispadne loše...
    @property
    def badFlagIndex(self):
        """
        Pomoćni property. Vraća boolean masku gdje su flagovi False, tj. lokaciju
        loših indeksa
        """
        flagovi = self.get_flags()
        losiIndeksi = flagovi == False
        return losiIndeksi

    @property
    def goodFlagIndex(self):
        """
        Pomoćni property. Vraća boolean masku gdje su flagovi True, tj. lokaciju
        dobrih indeksa
        """
        flagovi = self.get_flags()
        dobriIndeksi = flagovi == True
        return dobriIndeksi

    @property
    def badLDLIndex(self):
        """
        Pomoćni property. Vraća boolean masku gdje je korekcija ispod LDL.
        """
        losiLDL = (self._DF['korekcija'] < self._DF['LDL']).values.astype(np.bool)
        return losiLDL

    @property
    def startTime(self):
        """
        Pomoćni property. Vrijeme prvog indeksa u datafrejmu. Potrebno za crtanje granica
        ucitanih podataka.
        """
        # ucitavamo dan po dan, ovo je samo Test da li imamo ucitanih podataka u frejmu
        if len(self._DF) > 2:
            return self._DF.index[0]
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
    def ldl_line(self):
        """
        Pomoćni property. Vraća niz vrijednosti LDL iz datafrejma.
        """
        return np.array(self._DF['LDL'].values)

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
        #TODO! fix, samo 'flag' je bitan bez synca
        out = self.koncentracija_line # vrijednosti
        _flags = self._DF.loc[:,'flag'].values.copy()
        out[_flags==False] = np.NaN
        #out[self.badFlagIndex] = np.NaN # pretvori lose flagove u NaN
        return out

    @property
    def koncentracijaBad(self):
        """
        Pomoćni property. Vraća niz vrijednosti koncentracije iz datafrejma, ali
        u redovima gdje je flag True, koncentracije mjenjamo sa NaN.
        """
        #TODO! fix samo 'flag' je bitan bez synca
        out = self.koncentracija_line # vrijednosti
        _flags = self._DF.loc[:,'flag'].values.copy()
        out[_flags==True] = np.NaN
        #out[self.goodFlagIndex] = np.NaN # pretvori dobre flagove u NaN
        return out

    @property
    def korekcijaOk(self):
        """
        Pomoćni property. Vraća niz vrijednosti korekcije iz datafrejma, ali
        u redovima gdje je flag False, korekcije mjenjamo sa NaN.
        """
        out = self.korekcija_line # vrijednosti
        out[self.badFlagIndex] = np.NaN # pretvori lose flagove u NaN
        return out

    @property
    def korekcijaBad(self):
        """
        Pomoćni property. Vraća niz vrijednosti korekcije iz datafrejma, ali
        u redovima gdje je flag True, korekcije mjenjamo sa NaN.
        """
        out = self.korekcija_line # vrijednosti
        out[self.goodFlagIndex] = np.NaN # pretvori dobre flagove u NaN
        return out

    def get_korekcija_in_ppb(self):
        """
        Vrati korekcije, ali u ppb mjernim jedinicama za računanje NO2.
        """
        out = self.korekcija_line
        # ako je korekcija u ug/m3 pretvori u ppb
        if self.jedinica == 'ug/m3':
            out = out / self.unitConversionFactor
        return out
    
    def get_korekcija_broj_ispod_0(self):
        """
        Treba vratiti broj dobro flagiranih korekcija koji su ispod 0
        """
        with warnings.catch_warnings():
            # suppress warnings in context manager (all NaN slice encountered ...)
            # Problem nastaje kada dobijemo listu sa NaN podacima npr. NOx je negdje NaN gdje NO nije.
            # Usporedbe tada javljaju warning koji je u prinicipu bespotreban jer output logicke usporedbe
            # bilo čega sa NaN je False (što nama odgovara).
            warnings.simplefilter("ignore")
            out = np.less(self.korekcijaOk, 0)
        return np.nansum(out)
        

    def get_korekcija_broj_ispod_LDL(self):
        """
        Treba vratiti broj podataka koji su ispod LDL (po defaultu su krivi)
        """
        with warnings.catch_warnings():
            # suppress warnings in context manager (all NaN slice encountered ...)
            # Problem nastaje kada dobijemo listu sa NaN podacima npr. NOx je negdje NaN gdje NO nije.
            # Usporedbe tada javljaju warning koji je u prinicipu bespotreban jer output logicke usporedbe
            # bilo čega sa NaN je False (što nama odgovara).
            warnings.simplefilter("ignore")
            out = np.less(self.korekcija_line, self.ldl_line)
        return np.nansum(out)

    def get_pickle_map(self):
        """
        Funkcija za pomoć prilikom SAVE - LOAD operacija. Sprema sve bitne varijable
        u mapu.
        """
        mapa = {}
        mapa['kanalId'] = self.kanalId
        mapa['metaData'] = self.metaData
        mapa['status_code'] = self.status_code
        mapa['broj_u_satu'] = self.broj_u_satu
        mapa['dataframe'] = self.dataframe
        return mapa

    def set_pickle_map(self, mapa):
        """
        Funkcija za pomoć prilikom SAVE - LOAD operacija. Iz mape preuzima vrijednosti
        koje postavlja u zadane varijable.
        """
        self.kanalId = mapa['kanalId']
        self.metaData = mapa['metaData']
        self.status_code = mapa['status_code']
        self.broj_u_satu = mapa['broj_u_satu']
        self.dataframe = mapa['dataframe']

################################################################################
################################################################################
################################################################################
class KoncentracijaTablicaNO2(KoncentracijaTablica):
    """
    Klasa za model podataka koncentracije (tablica)

    #FUNKCIJE KOJE SMO PROMJENILI:
    _modify_LDL_status_and_flags - Kako nemamo LDL, u biti promjena flaga i statusa za LDL nema smisla
    _test_ispravnosti_korekcijske_tablice - Korekcijska tablica je drugog oblika (imamo samo stupac Ec)
    _pripremi_korekcijsku_tablicu - Korekcijska tablica je drugog oblika (imamo samo stupac Ec)
    apply_correction - primjena korekcije je drugačija, NO2 se računa iz NO i NOx korektiranih podataka u ppb

    mjerne jedinice????
    """
    def __init__(self):
        """Konstruktor klase."""
        super(KoncentracijaTablicaNO2, self).__init__()

    def _modify_LDL_status_and_flags(self):
        """
        Overload funkcije, u principu NO2 se računa iz NOx i NO, LDL ne mogu
        računati jer nemam A, B, Sr za NO2. Nema modificiranja statusa i flagova.
        """
        pass

    def _test_ispravnosti_korekcijske_tablice(self, korekcijskiFrejm):
        """
        Funkcija služi za provjeru svih potrebnih podataka u tablici korekcijskih
        parametara.
        """
        df = korekcijskiFrejm.copy()
        LEN1 = len(df)
        # inicijalni broj redova tablice
        # test za praznu tablicu
        if LEN1 == 0:
            #tablica je prazna
            return None #signal da napravimo fake tablicu sa nan vrijednostima
        # pobrini se da je Ec float vrijednost zbog racunanja
        df['Ec'] = df['Ec'].astype(float)
        # drop svih redova gdje imamo NaN vrijednosti
        df.dropna(axis=0, inplace=True)
        # korekcijska tablica ima stupac 'vrijeme', moramo ga prebaciti u indeks
        df = df.set_index(df['vrijeme'])
        df.drop('vrijeme', axis=1, inplace=True)
        # broj redova tablice sa izbacenim redovima sa NaN vrijednostima
        LEN2  = len(df)
        if LEN1 != LEN2:
            # ako LEN1 nije jednak LEN2 znaci da smo izbacili neki red - tablica nije dobro ispunjena
            raise ValueError('Parametri korekcije nisu dobro ispunjeni.')
        return df

    def _pripremi_korekcijsku_tablicu(self, korekcijskiFrejm):
        """
        Funkcija služi za pripremu i provjeru podataka efikasnosti konvertera Ec.
        """
        # provjera da li je tablica dobro ispunjena
        df = self._test_ispravnosti_korekcijske_tablice(korekcijskiFrejm)
        if df is None:
            #imamo praznu tablicu, fake output sa NaN vrijednostima
            out = pd.DataFrame(
                data={'Ec':np.NaN},
                columns=['Ec'],
                index=self._DF.index)
            # return all NaN table
            return out
        # u principu podatak o korekciji je sa vremenskim indeksom manjim od ucitanih podataka
        # potrebno je prosiriti kraj tablice korekcije za zadnjom vrijednosti
        zadnjiIndeksKorekcije = df.index[-1]
        zadnjiIndeksPodataka = self._DF.index[-1]
        if zadnjiIndeksKorekcije < zadnjiIndeksPodataka:
            #extend zadnje vrijednosti u tablici korekcije do kraja podataka
            df.loc[zadnjiIndeksPodataka, 'Ec'] = df.loc[zadnjiIndeksKorekcije, 'Ec']
        # ostali imaju "linearni" tip korekcije (NO2 kanal)
        df = df.resample('Min').interpolate()
        # reindex df radi preklapanja sa self._DF indeksima
        df = df.reindex(self._DF.index)
        return df

    def apply_correction(self, nox, no, correctFrame):
        """
        Funkcija služi za primjenu korekcije na ucitane podatke o koncentraciji.
        NO2 se računa iz korektiranih podataka nox i no u ppb mjernim jedinicama
        prema formuli:

        NO2 = (NOx-NO/Ec)*100

        correctFrame je dataframe sa podacima sa Ec za zadani kanal.
        nox je numpy array sa korektiranim NOx podacima u ppb-u
        no je numpy array sa korektiranim NO podacima u ppb-u

        Prilikom korekcije također se računa LDL vrijednost te se radi provjera da li
        su korigirani podaci iznad LDL (modifikacija flaga i statusa po potrebi).
        """
        df = correctFrame.copy()
        # priprema tablice korekcijskih parametara za rad sa podacima
        # -> inicijalni test, interpolacija, podesavanje indeksa sa glavnom tablicom
        df = self._pripremi_korekcijsku_tablicu(df)
        # racunanje korekcije u ppb
        korekcija = ((nox-no) / df.loc[:,'Ec'].values) * 100
        if self.jedinica == 'ppb':
            # tablica je u ppb modu i konverzija nije potrebna
            self._DF.loc[:,'korekcija'] = korekcija
        else:
            # tablica je u ug/m3 i potrebno je adaptirati vrijednosti iz ppb sustava
            korekcija = korekcija * self.unitConversionFactor
            self._DF.loc[:,'korekcija'] = korekcija
