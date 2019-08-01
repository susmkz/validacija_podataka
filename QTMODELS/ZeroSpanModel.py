#!/usr/bin/python3
# -*- coding: utf-8 -*-
import warnings
import numpy as np
import pandas as pd
from PyQt5 import QtCore


class ZeroSpanTablica(QtCore.QAbstractTableModel):
    """
    Klasa za modele podataka Zero i Span.
    """
    def __init__(self, tip, parent=None):
        super(ZeroSpanTablica, self).__init__(parent=parent)
        # definiranje vrste tablice ('zero' ili 'span') - naziv stupca sa nekorektiranim podacima
        self._tip = str(tip)
        # predvidjeni stupci u tablici sa podacima
        self._EXPECTED_COLUMNS = [str(tip), # 'zero' ili 'span' podaci
                                  'korekcija', # vrijednost korekcije zero ili spana
                                  'minDozvoljeno', # najmanja dozvoljena vrijednost
                                  'maxDozvoljeno', # najveca dozvoljena vrijednost
                                  'A', # parametar korekcije (nagib)
                                  'B', # parametar korekcije (odmak u "y" smjeru)
                                  'Sr', # parametar korekcije
                                  'LDL'] # low detection limit
        # pandas DataFrame sa podacima (sa zadanim stupcima)
        self._DF = pd.DataFrame(columns=self._EXPECTED_COLUMNS)
        # kanal Id - ID programa mjerenja iz baze
        self._kanalId = None
        # broj podataka u satu (neki loggeri nemaju minutno uzorkovanje)
        self._broj_u_satu = None
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
        Prikazujemo samo 4 stupca zbog smanjivanja podataka na ekranu:
            stupac 0 --> podaci za 'zero' ili 'span'
            stupac 1 --> korekcija
            stupac 2 --> minDozvoljeno
            stupac 3 --> maxDozvoljeno
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
            value = self._DF.iloc[row, col]
            return str(round(value, 3))
        # TOOLTIP ROLE - tooltip na mouseover ćelije
        if role == QtCore.Qt.ToolTipRole:
            value = self._DF.iloc[row, col]
            # vrati nezaokruzenu vrijednost
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
            # za stupce koristimo nazive stupaca datafrejma (prva 4 su u istom redosljedu)
            if role == QtCore.Qt.DisplayRole:
                return str(self._DF.columns[section])

    @property
    def tip(self):
        """Getter tipa tablice (naziv prvog stupca u datafrejmu) - 'zero' ili 'span'."""
        return self._tip

    @tip.setter
    def tip(self, x):
        """Setter tipa tablice (naziv prvog stupca u datafrejmu) - 'zero' ili 'span'."""
        self._tip = x

    @property
    def dataframe(self):
        """Getter datafrejma sa podacima (kopije)"""
        return self._DF.copy()

    @dataframe.setter
    def dataframe(self, x):
        """Setter datafrejma sa podacima (kopije)"""
        # preslagujemo stupce u odgovarajuci redosljed
        self._DF = x[self._EXPECTED_COLUMNS]
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
            if self.formula == 'NO2':
                #imamo praznu tablicu, fake output sa NaN vrijednostima
                out = pd.DataFrame(
                    data={'Ec':np.NaN},
                    columns=['Ec'],
                    index=self._DF.index)
            else:
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

    def apply_correction(self, correctFrame):
        """
        Funkcija služi za primjenu korekcije na ucitane podatke o koncentracije zero/span.
        Ulazni parametar correctFrame je dataframe sa podacima sa A, B, Sr za zadani kanal.

        Koristimo linearnu korekciju --> korekcija = A * koncentracija + B
        """
        #NO2 je special case, a ako nemamo podataka primjena korekcije nema smisla
        #Zero i Span frejmovi mogu biti prazni (kanali bez Z/S provjere itd... )- npr. kod PM
        if self.formula != 'NO2' and len(self._DF) > 0:
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
            korekcija = self._DF.loc[:,self.tip].values * self._DF.loc[:,'A'].values + self._DF.loc[:,'B'].values
            self._DF.loc[:,'korekcija'] = korekcija
        else:
            #NO2 je specijalni slučaj
            pass

    def initial_unit_conversion(self):
        """
        Ova funkcija se poziva samo jednom prilikom stvaranja sessiona, cilj je prebaciti mjerne jedinice
        koje app ocekuje u traženi sustav. Prilikom ucitavanja sve se automatski prebacuje u ug/m3.
        
        Zero i span podaci su inicijalno u ppb formatu ,prilikom ucitavanja sa REST-a
        te ih moramo inicijalno prebaciti u isti mjerni sustav kao i koncentracije (ug/m3...).

        - potrebno je promjeniti stupce self.tip ('zero' ili 'span') te stupce
        'minDozvoljeno' i 'maxDozvoljeno'
        """
        # PRETVARANJE U ug/m3 ili mg/m3
        for col in [self.tip, 'minDozvoljeno', 'maxDozvoljeno']:
            # dohvati stupac
            currentVals = self._DF.loc[:,col].values
            # primjeni konverziju u ug/m3 ili mg/m3
            newVals = currentVals * self.unitConversionFactor
            # postavi nove vrijednosti
            self._DF.loc[:,col] = newVals
        # singnal da je došlo do promjene u tablici
        self.layoutChanged.emit()

    def convert_units(self, ppx=True):
        """
        Funkcija pretvara vrijednosti u drugi sustav ovisno o parametru "ppx".
        Ako je "ppx" True, pretvaram u ppb ili ppm. Ako je "ppx" False, pretvaram
        u ug/m3 ili mg/m3. Model zna u kojim je mjernim jedinicama (metapodaci)
        te nakon promjene mora promjeniti metapodatke da reflektira promjenu.

        - Zero i span podaci su inicijalno u ppb formatu (prilikom ucitavanja te
        ih moramo inicijalno prebaciti i isti mjerni sustav kao i koncentracije.)

        - potrebno je promjeniti stupce self.tip ('zero' ili 'span') te stupce
        'minDozvoljeno' i 'maxDozvoljeno'

        - korekcija će se ponovno izračunati prilikom primjene korekcije.

        ispravak...
        promjenu metapodataka o jedinici ostavljamo funkciji koja zove ovu funkciju
        """
        if ppx and (self.jedinica not in ['ppb', 'ppm']):
            # PRETVARANJE U PPx (PPB ili PPM)
            for col in [self.tip, 'minDozvoljeno', 'maxDozvoljeno']:
                # dohvati stupac
                currentVals = self._DF.loc[:,col].values
                # primjeni konverziju u ppm ili ppb
                newVals = currentVals / self.unitConversionFactor
                # postavi nove vrijednosti
                self._DF.loc[:,col] = newVals
#            # postavi nove jedinice u metapodatke
#            if self.jedinica == 'ug/m3':
#                self.jedinica = 'ppb'
#            else:
#                self.jedinica = 'ppm'
        elif (not ppx) and (self.jedinica not in ['ug/m3', 'mg/m3']):
            # PRETVARANJE U ug/m3 ili mg/m3
            for col in [self.tip, 'minDozvoljeno', 'maxDozvoljeno']:
                # dohvati stupac
                currentVals = self._DF.loc[:,col].values
                # primjeni konverziju u ug/m3 ili mg/m3
                newVals = currentVals * self.unitConversionFactor
                # postavi nove vrijednosti
                self._DF.loc[:,col] = newVals
#            # postavi nove jedinice u metapodatke
#            if self.jedinica == 'ppb':
#                self.jedinica = 'ug/m3'
#            else:
#                self.jedinica = 'mg/m3'
        else:
            # nema potrebe za konverzijom (vec smo u dobrom sustavu)
            pass
        # singnal da je došlo do promjene u tablici
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

    @property
    def indeks(self):
        """
        Pomoćni property. Vraća potpuni indeks datafrejma (pandas timestampove).
        """
        return np.array(self._DF.index)

    @property
    def yPlotRange(self):
        """
        Pomoćni property. Raspon svih koncentracija (zero ili span) i korekcija prosiren za 20%.
        Izlaz je tuple sa (min, max) vrijednosti.
        """
        if len(self._DF):
            tmp1 = self._DF[self.tip].values.copy() # zero ili span
            tmp2 = self._DF['korekcija'].values.copy() # korekcije
            tmp3 = self._DF['minDozvoljeno'].values.copy() # minimalne dozvoljene vrijednosti
            tmp4 = self._DF['maxDozvoljeno'].values.copy() # maksimalne dozvoljene vrijednosti
            test1 = self._test_for_all_nan_range(tmp1) # ispravnost koncentracija
            test2 = self._test_for_all_nan_range(tmp2) # ispravnost korekcija
            test3 = self._test_for_all_nan_range(tmp3) # ispravnost min granice
            test4 = self._test_for_all_nan_range(tmp4) # ispravnost max granice
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
            # granice min
            if test3:
                lowlim = -1.0
            else:
                lowlim = np.nanmin(tmp3)
            # granice max
            if test4:
                highlim = 1.0
            else:
                highlim = np.nanmax(tmp4)
            # uzimamo manji od donjih granica i veci od gornjih granica
            od = np.min([lowKonc,lowKore,lowlim])
            do = np.max([highKonc,highKore,highlim])
            #odmaknimo granice malo dalje od ruba za 10% raspona u svakom smjeru
            raspon = (do - od)*0.1
            return (od-raspon, do+raspon)
        else:
            # ako nemamo podataka vrati default raspon za graf
            return (-1.0, 1.0)

    @property
    def baseline(self):
        """
        Pomoćni property. Vraća niz originalnih zero ili span iz datafrejma.
        """
        return np.array(self._DF[self.tip].values)

    @property
    def maxAllowed(self):
        """
        Pomoćni property. Vraća niz gornje dozvoljene granice iz datafrejma.
        """
        return np.array(self._DF['maxDozvoljeno'].values)

    @property
    def minAllowed(self):
        """
        Pomoćni property. Vraća niz donje dozvoljene granice iz datafrejma.
        """
        return np.array(self._DF['minDozvoljeno'].values)

    @property
    def korekcija(self):
        """
        Pomoćni property. Vraća niz korektiranih zero ili span podataka iz datafrejma.
        """
        return np.array(self._DF['korekcija'].values)

    def get_kriterij_ok(self, corr=False):
        """
        Funkcija vraća bool masku, dobri indeksi su True. Ako je corr==True, usporedjuje
        se korekcija, u protivnom se usporedjuje originialni span.

        Javlja se warning zbog usporedbi sa NaN vrijednostima pa privremeno gaismo warning tjekom
        izvođenja funkcije. To ne mjenja situaciju jer usporedba sa NaN je po defaultu False.
        """
        with warnings.catch_warnings():
            # suppress warnings u context manager-u
            warnings.simplefilter("ignore")
            if corr:
                # uporedba korekcije sa dozvoljenim granicama
                iznad = np.greater_equal(self.korekcija, self.minAllowed)
                ispod = np.less_equal(self.korekcija, self.maxAllowed)
                kriterij = np.logical_and(iznad,ispod)
            else:
                # uporedba zero/span sa dozvoljenim granicama
                iznad = np.greater_equal(self.baseline, self.minAllowed)
                ispod = np.less_equal(self.baseline, self.maxAllowed)
                kriterij = np.logical_and(iznad,ispod)
        return kriterij

    def get_kriterij_bad(self, corr=False):
        """
        Funkcija vraća bool masku, losi indeksi su True. Ako je corr==True, usporedjuje
        se korekcija, u protivnom se usporedjuje originialni span.
        """
        # trazimo tamo gdje je kriterij dobar
        kriterij = self.get_kriterij_ok(corr=corr)
        # logical NOT okrece kriterij na suprotnu stranu
        return np.logical_not(kriterij)

    @property
    def korekcijaOk(self):
        """
        Pomoćni property. Vraća niz vrijednosti korekcije iz datafrejma, ali
        u redovima gdje je flag False, korekcije mjenjamo sa NaN.
        """
        kriterij = self.get_kriterij_bad(corr=True)
        out = self.korekcija
        out[kriterij] = np.NaN
        return out

    @property
    def korekcijaBad(self):
        """
        Pomoćni property. Vraća niz vrijednosti korekcije iz datafrejma, ali
        u redovima gdje je flag True, korekcije mjenjamo sa NaN.
        """
        kriterij = self.get_kriterij_ok(corr=True)
        out = self.korekcija
        out[kriterij] = np.NaN
        return out

    @property
    def spanOk(self):
        """
        Pomoćni property. Vraća niz vrijednosti zero ili span iz datafrejma, ali
        u redovima gdje je flag False, korekcije mjenjamo sa NaN.
        """
        kriterij = self.get_kriterij_bad(corr=False)
        out = self.korekcija
        out[kriterij] = np.NaN
        return out

    @property
    def spanBad(self):
        """
        Pomoćni property. Vraća niz vrijednosti zero ili span iz datafrejma, ali
        u redovima gdje je flag True, korekcije mjenjamo sa NaN.
        """
        kriterij = self.get_kriterij_ok(corr=False)
        out = self.korekcija
        out[kriterij] = np.NaN
        return out

    def get_pickle_map(self):
        """
        Funkcija za pomoć prilikom SAVE - LOAD operacija. Sprema sve bitne varijable
        u mapu.
        """
        mapa = {}
        mapa['dataframe'] = self.dataframe
        mapa['kanalId'] = self.kanalId
        mapa['metaData'] = self.metaData
        mapa['broj_u_satu'] = self.broj_u_satu
        mapa['tip'] = self.tip
        return mapa

    def set_pickle_map(self, mapa):
        """
        Funkcija za pomoć prilikom SAVE - LOAD operacija. Iz mape preuzima vrijednosti
        koje postavlja u zadane varijable.
        """
        self.tip = mapa['tip']
        self._EXPECTED_COLUMNS = [str(self.tip),
                                  'korekcija',
                                  'minDozvoljeno',
                                  'maxDozvoljeno',
                                  'A',
                                  'B',
                                  'Sr',
                                  'LDL']
        self.kanalId = mapa['kanalId']
        self.metaData = mapa['metaData']
        self.broj_u_satu = mapa['broj_u_satu']
        self.dataframe = mapa['dataframe']
