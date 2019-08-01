#!/usr/bin/python3
# -*- coding: utf-8 -*-
from app.QTMODELS.KoncentracijaModel import KoncentracijaTablica
from app.QTMODELS.KoncentracijaModel import KoncentracijaTablicaNO2
from app.QTMODELS.SatniModel import SatniTablica
from app.QTMODELS.KorekcijaModel import KorekcijaTablica
from app.QTMODELS.KorekcijaModel import KorekcijaTablicaNO2
from app.QTMODELS.ZeroSpanModel import ZeroSpanTablica


class DataStore(object):
    """
    Klasa za "spremište" podataka jednog kanala.
    Spremaju se metapodaci, ID kanala, broj podataka u satu, te potrebni QT modeli
    """
    def __init__(self):
        """
        Konstruktor klase
        """
        self._kanalId = None # id kanala (programMjerenjaId)
        self._broj_u_satu = None # broj podataka u satu
        self._metaData = {} # mapa sa metapodacima za kanal (postaja, jedinica ...)
        # QT modeli
        self._modelKonc = KoncentracijaTablica()
        self._modelSatni = SatniTablica()
        self._modelCorr = KorekcijaTablica()
        self._modelZero = ZeroSpanTablica('zero')
        self._modelSpan = ZeroSpanTablica('span')

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
    def isNOx(self):
        """ True ako je formula metapodataka u NOx grupi. """
        return self.formula in ['NOx', 'NO', 'NO2']

    @property
    def isPM(self):
        """ True ako je formula metapodataka u PM grupi. """
        return self.formula in ['PM10', 'PM1', 'PM2.5']

    @property
    def puniOpis(self):
        """Getter punog opisa iz metapodataka (postaja : formula mjerna_jedinica)."""
        return "{0} : {1} {2}".format(self.postaja, self.formula, self.jedinica)

    @property
    def opis(self):
        """Getter kratkog opisa iz metapodataka (postaja : formula)."""
        return "{0} : {1}".format(self.postaja, self.formula)

    def set_koncentracija(self, kanal, meta, frejm, status_code, broj_u_satu):
        """
        Funkcija postavlja podatake koncentracije u datastore nakon ucitavanja novih podataka
        """
        #NO2 ima drugačiju tablicu, provjera formule iz metapodataka
        if meta.get('komponentaFormula', '???') == 'NO2':
            # postavljanje posebne tablice za NO2
            self._modelKonc = KoncentracijaTablicaNO2()
        self.koncentracija.kanalId = kanal
        self.koncentracija.broj_u_satu = broj_u_satu
        self.koncentracija.metaData = meta
        self.koncentracija.status_code = status_code
        self.koncentracija.dataframe = frejm

    def set_satni(self, kanal, meta, frejm, status_code, broj_u_satu):
        """
        Funkcija postavlja satno agregirane podatake koncentracije u datastore nakon
        ucitavanja novih podataka. "frejm" mora biti minutne (ili sub-satne) rezolucije.
        Setter dataframe satno agregiranog modela automatski agregira podatke
        """
        self.satni.kanalId = kanal
        self.satni.broj_u_satu = broj_u_satu
        self.satni.metaData = meta
        self.satni.status_code = status_code
        self.satni.dataframe = frejm #frejm se automatski agregira prilikom postavljanja

    def set_zero(self, kanal, meta, frejm, broj_u_satu):
        """
        Funkcija postavlja podatake ZERO u datastore nakon ucitavanja novih podataka
        """
        self.zero.kanalId = kanal
        self.zero.broj_u_satu = broj_u_satu
        self.zero.metaData = meta
        self.zero.dataframe = frejm

    def set_span(self, kanal, meta, frejm, broj_u_satu):
        """
        Funkcija postavlja podatake SPAN u datastore nakon ucitavanja novih podataka
        """
        self.span.kanalId = kanal
        self.span.broj_u_satu = broj_u_satu
        self.span.metaData = meta
        self.span.dataframe = frejm

    def set_korekcija(self, kanal, meta, frejm):
        """
        Funkcija postavlja podatake korekcije u datastore nakon ucitavanja novih podataka
        """
        #NO2 ima drugačiju tablicu, provjera formule iz metapodataka
        if meta.get('komponentaFormula', '???') == 'NO2':
            # postavljanje posebne tablice za NO2
            self._modelCorr = KorekcijaTablicaNO2()
        self.korekcija.kanalId = kanal
        self.korekcija.metaData = meta
        self.korekcija.dataframe = frejm

    @property
    def koncentracija(self):
        """Getter modela koncentracije."""
        return self._modelKonc

    @property
    def satni(self):
        """Getter modela satno agregiranih koncentracija."""
        return self._modelSatni

    @property
    def korekcija(self):
        """Getter modela korekcijske tablice."""
        return self._modelCorr

    @property
    def zero(self):
        """Getter modela zero."""
        return self._modelZero

    @property
    def span(self):
        """Getter modela span."""
        return self._modelSpan

    def store2dict(self):
        """
        Funkcija za pomoć prilikom SAVE - LOAD operacija. Sprema sve bitne varijable
        u mapu.
        """
        out = {}
        out['kanalId'] = self.kanalId
        out['broj_u_satu'] = self.broj_u_satu
        out['metaData'] = self.metaData
        out['koncentracija'] = self.koncentracija.get_pickle_map()
        out['satni'] = self.satni.get_pickle_map()
        out['korekcija'] = self.korekcija.get_pickle_map()
        out['zero'] = self.zero.get_pickle_map()
        out['span'] = self.span.get_pickle_map()
        return out

    def dict2store(self, mapa):
        """
        Funkcija za pomoć prilikom SAVE - LOAD operacija. Iz mape preuzima vrijednosti
        koje postavlja u zadane varijable.
        """
        self.kanalId = mapa['kanalId']
        self.broj_u_satu = mapa['broj_u_satu']
        self.metaData = mapa['metaData']
        #NO2 ima drugačiju tablicu, provjera formule iz metapodataka
        if self.metaData.get('komponentaFormula', '???') == 'NO2':
            # postavljanje posebnih tablice za NO2
            self._modelKonc = KoncentracijaTablicaNO2()
            self._modelCorr = KorekcijaTablicaNO2()
        self.koncentracija.set_pickle_map(mapa['koncentracija'])
        self.satni.set_pickle_map(mapa['satni'])
        self.korekcija.set_pickle_map(mapa['korekcija'])
        self.zero.set_pickle_map(mapa['zero'])
        self.span.set_pickle_map(mapa['span'])
