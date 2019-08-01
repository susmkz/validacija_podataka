#!/usr/bin/python3
# -*- coding: utf-8 -*-
import pickle
from app.DOCUMENT.Datastore import DataStore


class Session(object):
    """
    Klasa za čuvanje podataka o Sessionu (radni set podataka)
    """
    def __init__(self, podaci, filename=None):
        """
        Konstruktor klase.

        podaci : mapa kanala koji se trebaju ucitati
            -kanalId (key)
            -broj_u_satu (broj podataka u satu)
            -metaData
            -status_code (int2string)
            -koncentracija frejm
            -zero frejm
            -span frejm
            -korekcija frejm

        filename = spremljeni session, ako je filename zadan, load iz filea
        """
        # interni spremnik (mapa) za podatke o kanalu (pojedini Datastore)
        self._datastoreMap = {}
        if filename != None:
            # load iz file-a
            self.load_from_file(filename)
        else:
            # moramo konzistentno spremiti dobivene podatke
            for kanal, mapa in podaci.items():
                meta = mapa['metaData']
                status_code = mapa['status_code']
                broj_u_satu = mapa['broj_u_satu']
                self._datastoreMap[kanal] = DataStore()
                self._datastoreMap[kanal].kanalId = kanal
                self._datastoreMap[kanal].metaData = meta
                self._datastoreMap[kanal].set_koncentracija(kanal, meta, mapa['koncentracija'], status_code, broj_u_satu)
                self._datastoreMap[kanal].set_satni(kanal, meta, mapa['koncentracija'], status_code, broj_u_satu)
                self._datastoreMap[kanal].set_zero(kanal, meta, mapa['zero'], broj_u_satu)
                self._datastoreMap[kanal].set_span(kanal, meta, mapa['span'], broj_u_satu)
                self._datastoreMap[kanal].set_korekcija(kanal, meta, mapa['korekcija'])
                #zero i span tablice su po defaultu u ppb ili ppm formatu nakon ucitavanja.
                #dok su ostali podaci u ug/m3 ili mg/m3. moramo uskladiti mjerne sustave
                #tako da prebacujemo zero i span podatke u ug/m3 ili mg/m3.
                self._datastoreMap[kanal].zero.initial_unit_conversion()
                self._datastoreMap[kanal].span.initial_unit_conversion()

    def get_datastore(self, kanal):
        """
        Vrati instancu Datastore za trazeni kanal
        """
        return self._datastoreMap[kanal]

    @property
    def sviKanali(self):
        """
        Getter sortirane liste učitanih kanala (programa mjerenja) - lista sortiranih
        integera.
        """
        return sorted(list(self._datastoreMap.keys()))

    def get_mapu_kanala_ID_OPIS(self):
        """
        Vrati mapu kanala kanalId/opis
        """
        out = {}
        for kanal in self.sviKanali:
            out[kanal] = self.get_datastore(kanal).koncentracija.opis
        return out

    def get_mapu_kanala_ID_JEDINICA(self):
        """
        Vrati mapu kanala kanalId/opis
        """
        out = {}
        for kanal in self.sviKanali:
            out[kanal] = self.get_datastore(kanal).koncentracija.jedinica
        return out

    
    def get_grupirane_kanale(self):
        """
        Cilj je dohvatiti sve grupe kanala (setove) kao listu zbog lakseg uskladjivanja kanala.
        """
        # svi dostupni
        svi = set(self.sviKanali)
        out = list()
        while len(svi): # dokle god ima vrijednosti u setu svih
            grupa = set() # definiramo grupu
            kanal = svi.pop() #dodajemo prvi element iz seta svih (ujedino ga i brišemo iz seta svih) u grupu
            grupa.add(kanal) # dodavanje u grupu
            #pronalazak povezanih
            povezani = self.get_datastore(kanal).koncentracija.povezaniKanali
            for i in povezani:
                grupa.add(i) # kako dodajemo povezane
                svi.discard(i) # tako ih brisemo iz seta svih dostupnih
            out.append(grupa)
        return out

    def get_ostale_kanale(self, x):
        """
        Vrati popis svih kanala osim zadanog (x)
        """
        out = self.sviKanali
        out.remove(x)
        return out

    def save_to_file(self, filename):
        """
        Spremi Session u file (binary dump podataka).
        """
        outMap = {}
        for kanal in self._datastoreMap:
            # svaki pojedini Datastore se zna zapakirati u mapu (dictionary)
            outMap[kanal] = self._datastoreMap[kanal].store2dict()
        # serialize u binary string
        binstr = pickle.dumps(outMap)
        # zapis u file
        with open(filename, 'wb') as f:
            f.write(binstr)

    def load_from_file(self, filename):
        """
        Load Session iz filea (binary read podataka).
        """
        # clear datastore mape
        self._datastoreMap = {}
        # citanje filea
        with open(filename, 'rb') as f:
            binstr = f.read()
            inMap = pickle.loads(binstr)
            # za svaki kanal moramo dodati element u _datastoreMap
            for kanal in inMap:
                # stvaramo instancu Datastore
                self._datastoreMap[kanal] = DataStore()
                # instanca Datastore zna se otpakirati iz mape (dictionary)
                self._datastoreMap[kanal].dict2store(inMap[kanal])
