#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import logging
import requests
import datetime
import numpy as np
import pandas as pd
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
from PyQt5 import QtWidgets, QtCore


class RESTZahtjev(object):
    """
    Klasa zadužena za komunikaciju sa REST servisom
    BITNE FUNKCIJE:
    -> logmein :: log in
    -> logmeout :: log out
    -> get_programe_mjerenja :: dohvati podatke o stanici/mjerenju
    -> get_statusMap :: dohvaca status mapu flagova {bit:opisni string}
    -> get_broj_u_satu :: broj podataka u satu (sampling rate) za neki program mjerenja
    -> get_sirovi :: dohvacanje sirovih podataka
    -> get_zero_span :: dohvacanje podataka za zero i span (tuple)
    """
    def __init__(self, konfig, auth=("","")):
        """Konstruktor klase. Klasa se inicijalizira sa konfig objektom (koji sadrži bitne
        podatke za REST - adrese) i autorizacijskim tupleom (user, password) koji je po
        defaultu prazan."""
        self.konfig = konfig # konfiguracijski objekt
        self.logmein(auth) # postavljanje log_in podataka o korisniku
        # inicijalno citanje konfiga sa ciljem da zapamtimo podatke o REST servisu
        self.urlProgramMjerenja = self.konfig.get_konfig_option('REST', 'program_mjerenja', '')
        self.urlSiroviPodaci = self.konfig.get_konfig_option('REST', 'sirovi_podaci', '')
        self.urlStatusMap = self.konfig.get_konfig_option('REST', 'status_map', '')
        self.urlZeroSpan = self.konfig.get_konfig_option('REST', 'zero_span_podaci', '')
        # ocekivani stupci u outputu - cilj je dobro pripremiti ulazne podatke za rad sa modelima
        # ocekivani stupci u outputu za koncentracijsku tablicu
        self.expectedColsKonc = ['koncentracija', 'korekcija', 'flag',
                                 'status', 'id', 'A', 'B', 'Sr', 'LDL', 'logical_flag', 'sync_flag']
        # ocekivani stupci u outputu za zero tablicu
        self.expectedColsZero = ['zero', 'korekcija', 'minDozvoljeno',
                                 'maxDozvoljeno', 'A', 'B', 'Sr', 'LDL']
        # ocekivani stupci u outputu za span tablicu
        self.expectedColsSpan = ['span', 'korekcija', 'minDozvoljeno',
                                 'maxDozvoljeno', 'A', 'B', 'Sr', 'LDL']

    def logmein(self, auth):
        """Funkcija postavlja user i password u objekt."""
        self.user, self.pswd = auth

    def logmeout(self):
        """Funkcija postavlja prazan ("") user i password u objekt. Log out operaicija jer
        brišemo sve podatke za login iz memorije."""
        self.user, self.pswd = ("", "")

    def get_broj_u_satu(self, programMjerenjaId):
        """
        Metoda dohvaca broj podataka u satu za neki programMjerenjaID (neka mjerenja
        nemaju minutnu rezoluciju). Output je integer.
        """
        # sastavljanje url stringa za REST
        url = "".join([self.urlProgramMjerenja, '/podaci/',str(programMjerenjaId)])
        # sastavljanje headera zahtjeva
        head = {"accept":"application/json"}
        # upit prema REST servisu (preko HTTP-a)
        r = requests.get(url,
                         timeout=15.1,
                         headers=head,
                         auth=HTTPBasicAuth(self.user, self.pswd))
        # priprema poruke o statusu (za slučaj neuspjeha)
        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
        # assert da je request OK, u slučaju loseg requesta - AssertionError sa porukom "msg"
        assert r.ok == True, msg
        # tekst poruke je json tekst - zanima nas samo 'brojUSatu' pretvoren u integer
        out = json.loads(r.text)
        return int(out['brojUSatu'])

    def get_programe_mjerenja(self):
        """
        Metoda salje zahtjev za svim programima mjerenja prema REST servisu.
        Uz pomoc funkcije parse_xml, prepakirava dobivene podatke u mapu
        'zanimljivih' podataka. Vraca (nested) dictionary programa mjerenja ili
        prazan dictionary u slucaju pogreske prilikom rada.
        """
        # sastavljanje url stringa za REST
        url = self.urlProgramMjerenja
        # sastavljanje headera zahtjeva
        head = {"accept":"application/xml"}
        # sastavljanje parametara zahtjeva
        payload = {"id":"findAll", "name":"GET"}
        # upit prema REST servisu (preko HTTP-a)
        r = requests.get(url,
                         params=payload,
                         timeout=39.1,
                         headers=head,
                         auth=HTTPBasicAuth(self.user, self.pswd))
        # priprema poruke o statusu (za slučaj neuspjeha)
        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
        # assert da je request OK, u slučaju loseg requesta - AssertionError sa porukom "msg"
        assert r.ok == True, msg
        # tekst poruke je XML tekst - potrebno ga je parsati u python dictionary (nested)
        out = self.parse_mjerenjaXML(r.text)
        return out

    def get_statusMap(self):
        """
        Metoda dohvaca podatke o statusima sa REST servisa
        vraca mapu (dictionary):
        {broj bita [int] : opisni string [str]}
        """
        # sastavljanje url stringa za REST
        url = self.urlStatusMap
        # sastavljanje headera zahtjeva
        head = {"accept":"application/json"}
        # upit prema REST servisu (preko HTTP-a)
        r = requests.get(url,
                         timeout=15.1,
                         headers = head,
                         auth=HTTPBasicAuth(self.user, self.pswd))
        # priprema poruke o statusu (za slučaj neuspjeha)
        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
        # assert da je request OK, u slučaju loseg requesta - AssertionError sa porukom "msg"
        assert r.ok == True, msg
        # tekst poruke je json tekst
        jsonStr = r.text
        x = json.loads(jsonStr) #convert u dictionary - svaki element ima ['i'] - integer i  ['s'] - string
        rezultat = {}
        # preslagaivanje u traženi oblik
        for i in range(len(x)):
            rezultat[x[i]['i']] = x[i]['s']
        return rezultat

    def get_inverseStatusMap(self):
        """
        Metoda dohvaca podatke o statusima sa REST servisa
        vraca mapu (dictionary):
        {opisni string [str]:broj bita [int]}
        """
        # dohvati mapu int - str
        mapa = self.get_statusMap()
        # inverz mape
        out = dict(zip(mapa.values(), mapa.keys()))
        return out

    def get_sirovi(self, programMjerenjaId, datum):
        """
        Za zadani program mjerenja (int) i datum (string, formata YYYY-MM-DD)
        dohvati sirove (minutne) podatke sa REST servisa.
        Output funkcije je json string.
        """
        # sastavljanje url stringa za REST
        url = "/".join([self.urlSiroviPodaci, str(programMjerenjaId), datum])
        # sastavljanje parametara zahtjeva
        payload = {"id":"getPodaci", "name":"GET", "broj_dana":1}
        # sastavljanje headera zahtjeva
        head = {"accept":"application/json"}
        # upit prema REST servisu (preko HTTP-a)
        r = requests.get(url,
                         params=payload,
                         timeout=39.1,
                         headers=head,
                         auth=HTTPBasicAuth(self.user, self.pswd))
        # priprema poruke o statusu (za slučaj neuspjeha)
        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
        # assert da je request OK, u slučaju loseg requesta - AssertionError sa porukom "msg"
        assert r.ok == True, msg
        # pretvaranje json teksta u dobro oblikovani pandas dataframe
        frejm = self.adaptiraj_ulazni_json(r.text)
        return frejm

    def get_zero_span(self, programMjerenja, datum, kolicina):
        """
        Dohvati zero-span vrijednosti
        ulazni parametri su:
        -programMjerenja : integer, id programa mjerenja
        -datum : string formata 'YYYY-MM-DD'
        -kolicina : integer, broj dana koji treba dohvatiti

        Funkcija vraca json string sa trazenim podacima ili prazan string ako je
        doslo do problema prilikom rada.
        """
        # sastavljanje url stringa za REST
        url = "/".join([self.urlZeroSpan, str(programMjerenja), datum])
        # sastavljanje parametara zahtjeva
        payload = {"id":"getZeroSpanLista", "name":"GET", "broj_dana":int(kolicina)}
        # sastavljanje headera zahtjeva
        head = {"accept":"application/json"}
        # upit prema REST servisu (preko HTTP-a)
        r = requests.get(url,
                         params=payload,
                         timeout=39.1,
                         headers=head,
                         auth=HTTPBasicAuth(self.user, self.pswd))
        # priprema poruke o statusu (za slučaj neuspjeha)
        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
        # assert da je request OK, u slučaju loseg requesta - AssertionError sa porukom "msg"
        assert r.ok == True, msg
        # pretvaranje json teksta u odgovarajuće datafrejmove za zero i span
        zero, span = self.adaptiraj_zero_span_json(r.text)
        return zero, span

    def adaptiraj_zero_span_json(self, x):
        """
        Funkcija je zaduzena da konvertira ulazni json string zero i span podataka (x)
        u pandas DataFrame. Podaci su izmjesani za zero i span u jednoj tablici, potrebno
        ih je razdvojiti.
        """
        try:
            # direktno citanje jsona u datafrejm
            frejm = pd.read_json(x, orient='records', convert_dates=['vrijeme'])
            if len(frejm) == 0:
                #slučaj kada nemamo podataka
                logging.info('Nema dostupnih podataka za ZERO i SPAN.')
                spanFrejm = pd.DataFrame(columns=self.expectedColsSpan)
                zeroFrejm = pd.DataFrame(columns=self.expectedColsZero)
                return zeroFrejm, spanFrejm
            # provjera da li su svi potrebni stupci na broju
            assert 'vrsta' in frejm.columns, 'Nedostaje stupac vrsta'
            assert 'vrijeme' in frejm.columns, 'Nedostaje stupac vrijeme'
            assert 'vrijednost' in frejm.columns, 'Nedostaje stupac vrijednost'
            assert 'minDozvoljeno' in frejm.columns, 'Nedostaje stupac minDozvoljeno'
            assert 'maxDozvoljeno' in frejm.columns, 'Nedostaje stupac maxDozvoljeno'
            # split na zero i span frejm (preko stupca 'vrsta')
            zeroFrejm = frejm[frejm['vrsta'] == "Z"]
            spanFrejm = frejm[frejm['vrsta'] == "S"]
            # reset indeksa
            zeroFrejm = zeroFrejm.set_index(zeroFrejm['vrijeme'])
            spanFrejm = spanFrejm.set_index(spanFrejm['vrijeme'])
            # zaokruživanje vremena indeksa na minutnu razinu
            zeroIndeksRounded = [i.round('Min') for i in zeroFrejm.index]
            spanIndeksRounded = [i.round('Min') for i in spanFrejm.index]
            # postavljanje zaokruženih indeksa
            zeroFrejm.index = zeroIndeksRounded
            spanFrejm.index = spanIndeksRounded
            # drop stupaca koje ne koristimo :vrsta, vrijeme (sada je indeks frejmova)
            spanFrejm.drop(['vrijeme', 'vrsta'], inplace=True, axis=1)
            zeroFrejm.drop(['vrijeme', 'vrsta'], inplace=True, axis=1)
            # promjena naziva stupca - mjenjamo 'vrijednost' u 'zero' i 'span'
            spanFrejm.rename(columns={'vrijednost':'span'}, inplace=True)
            zeroFrejm.rename(columns={'vrijednost':'zero'}, inplace=True)
            # dodajemo stupce koji nedostaju (NaN vrijednosti)
            spanFrejm['korekcija'] = np.NaN
            spanFrejm['A'] = np.NaN
            spanFrejm['B'] = np.NaN
            spanFrejm['Sr'] = np.NaN
            spanFrejm['LDL'] = np.NaN
            zeroFrejm['korekcija'] = np.NaN
            zeroFrejm['A'] = np.NaN
            zeroFrejm['B'] = np.NaN
            zeroFrejm['Sr'] = np.NaN
            zeroFrejm['LDL'] = np.NaN
            # preslagivanje redosljeda stupaca u ocekivani redosljed
            spanFrejm = spanFrejm[self.expectedColsSpan]
            zeroFrejm = zeroFrejm[self.expectedColsZero]
            return zeroFrejm, spanFrejm
        except Exception:
            # u slučaju pogreške vrati prazan datafrejm za zero i span
            logging.error('Fail kod parsanja json stringa:\n'+str(x), exc_info=True)
            spanFrejm = pd.DataFrame(columns=self.expectedColsSpan)
            zeroFrejm = pd.DataFrame(columns=self.expectedColsZero)
            return zeroFrejm, spanFrejm

    def adaptiraj_ulazni_json(self, x):
        """
        Funkcija je zaduzena da konvertira ulazni json string podataka koncentracije (x)
        u pandas DataFrame.
        """
        try:
            # direktno citanje jsona u datafrejm
            df = pd.read_json(x, orient='records', convert_dates=['vrijeme'])
            # provjera da li su svi potrebni stupci na broju
            assert 'vrijeme' in df.columns, 'ERROR - Nedostaje stupac: "vrijeme"'
            assert 'id' in df.columns, 'ERROR - Nedostaje stupac: "id"'
            assert 'vrijednost' in df.columns, 'ERROR - Nedostaje stupac: "vrijednost'
            assert 'valjan' in df.columns, 'ERROR - Nedostaje stupac: "valjan"'
            assert 'statusInt' in df.columns, 'ERROR - Nedostaje stupac: "statusInt"'
            assert 'nivoValidacije' in df.columns, 'Error - Nedostaje stupac: "nivoValidacije"'
            # postavljanje vremenskog indeksa
            df = df.set_index(df['vrijeme'])
            # rename stupaca
            renameMap = {'vrijednost':'koncentracija',
                         'valjan':'flag',
                         'statusInt':'status'}
            df.rename(columns=renameMap, inplace=True)
            # konverzija ulaznih podataka
            df['koncentracija'] = df['koncentracija'].map(self._nan_conversion)
            df['flag'] = df['flag'].map(self._valjan_conversion)
            # definiranje stupaca koji nedostaju (NaN vrijednosti)
            df['korekcija'] = np.NaN
            df['A'] = np.NaN
            df['B'] = np.NaN
            df['Sr'] = np.NaN
            df['LDL'] = np.NaN
            # za boolean stupce moramo srediti da su svi True
            allTrue = np.empty(len(df), dtype=np.bool)
            allTrue.fill(True)
            df['logical_flag'] = allTrue.copy() #logical flag (npr. PM10 > PM1)
            df['sync_flag'] = allTrue.copy() #sync flag (povezani kanali moraju biti usklađeni)
            # drop srupaca koji se ne koriste
            df.drop(['vrijeme', 'nivoValidacije'], inplace=True, axis=1)
            # preslagivanje redosljeda stupaca u ocekivani redosljed
            df = df[self.expectedColsKonc]
            return df
        except (ValueError, TypeError, AssertionError):
            # u slučaju pogreške vrati prazan datafrejm
            logging.error('Fail kod parsanja json stringa:\n'+str(x), exc_info=True)
            df = pd.DataFrame(columns=self.expectedColsKonc)
            return df

    def parse_mjerenjaXML(self, x):
        """
        Parse XML sa programima mjerenja preuzetih sa REST servisa,

        output: (nested) dictionary sa bitnim podacima. Primarni kljuc je program
        mjerenja id, sekundarni kljucevi su opisni (npr. 'komponentaNaziv')
        """
        # priprema izlazne mape sa podacima
        rezultat = {}
        # za XML parse koristimo ElementTree parser
        root = ET.fromstring(x)
        for programMjerenja in root:
            i = int(programMjerenja.find('id').text)
            postajaId = int(programMjerenja.find('.postajaId/id').text)
            postajaNaziv = programMjerenja.find('.postajaId/nazivPostaje').text
            komponentaId = programMjerenja.find('.komponentaId/id').text
            komponentaNaziv = programMjerenja.find('.komponentaId/naziv').text
            komponentaMjernaJedinica = programMjerenja.find('.komponentaId/mjerneJediniceId/oznaka').text
            komponentaFormula = programMjerenja.find('.komponentaId/formula').text
            usporednoMjerenje = programMjerenja.find('usporednoMjerenje').text
            konvVUM = float(programMjerenja.find('.komponentaId/konvVUM').text) #konverizijski volumen
            # dodavanje mjerenja u izlaznu mapu pod ključem programa mjerenja
            rezultat[i] = {
                'postajaId':postajaId,
                'postajaNaziv':postajaNaziv,
                'komponentaId':komponentaId,
                'komponentaNaziv':komponentaNaziv,
                'komponentaMjernaJedinica':komponentaMjernaJedinica,
                'komponentaFormula':komponentaFormula,
                'usporednoMjerenje':usporednoMjerenje,
                'konvVUM':konvVUM,
                'povezaniKanali':[i]}
        return rezultat

    def _valjan_conversion(self, x):
        """
        Pomocna funkcija, inicijalni test valjanosti podataka
        """
        if x:
            return True
        else:
            return False

    def _nan_conversion(self, x):
        """
        Pomocna funkcija, mjenja male argumente u np.NaN
        """
        if x > -9999:
            return x
        else:
            return np.NaN


class DataReaderAndCombiner(object):
    """
    Klasa za čitanje podataka sa REST servisa. Čita se dan po dan, update progress bara i
    spajanje dnevnih frejmova u jedan izlazni frejm.

    reader : RestZahtjev objekt - potreban za dohvaćanje dnevnih frejmova
    parent : instanca glavnog prozora aplikacije - potrebna za definiranje parenta QProgressBar-a
    """
    def __init__(self, reader, parent):
        """
        Konstruktor klase. Inicijalizacija sa RestZahtjev objektom i instancom glavnog prozora aplikacije.
        """
        self.citac = reader
        self.parent = parent
        # mapa za kodiranje / dekodiranje statusa
        self.bitFlagInfo = self.citac.get_inverseStatusMap()
        # tražimo status "NEDOSTAJE" zbog nadopunjavanja tablice
        self.NEDOSTAJE = 2**self.bitFlagInfo['NEDOSTAJE'] #vrijednost za flag
        # ocekivani stupci u outputu - cilj je dobro pripremiti ulazne podatke za rad sa modelima
        # ocekivani stupci u outputu za koncentracijsku tablicu
        self.expectedColsKonc = ['koncentracija', 'korekcija', 'flag',
                                 'status', 'id', 'A', 'B', 'Sr', 'LDL', 'logical_flag', 'sync_flag']
        # ocekivani stupci u outputu za zero tablicu
        self.expectedColsZero = ['zero', 'korekcija', 'minDozvoljeno',
                                 'maxDozvoljeno', 'A', 'B', 'Sr', 'LDL']
        # ocekivani stupci u outputu za span tablicu
        self.expectedColsSpan = ['span', 'korekcija', 'minDozvoljeno',
                                 'maxDozvoljeno', 'A', 'B', 'Sr', 'LDL']

    def get_data(self, kanal, od, do):
        """
        Glavna funkcija za dohvaćanje podataka sa RESTA
        in:
        -kanal: id kanala mjerenja
        -od: datetime.datetime (pocetak)
        -do: datetime.datetime (kraj)
        """
        try:
            #prazni frejmovi u koje ce se spremati podaci
            masterKoncFrejm = pd.DataFrame(columns=self.expectedColsKonc)
            masterZeroFrejm = pd.DataFrame(columns=self.expectedColsZero)
            masterSpanFrejm = pd.DataFrame(columns=self.expectedColsSpan)
            #definiraj raspon podataka (poteban za popunjavanje tablice)
            timeRaspon = od.daysTo(do)
            if timeRaspon < 1:
                raise ValueError('Vremenski raspon manji od dana nije dozvoljen')
            # napravi instancu progress bara i postavi ga u glavni prozor aplikacije
            self.progressbar = QtWidgets.QProgressBar(parent=self.parent)
            self.progressbar.setWindowTitle('Učitavanje podataka:')
            self.progressbar.setRange(0, timeRaspon+1)
            self.progressbar.setGeometry(300, 300, 200, 40)
            self.progressbar.show()
            # ucitavanje frejmova koncentracija, zero, span
            for d in range(timeRaspon+1):
                dan = (od.addDays(d)).toString(QtCore.Qt.ISODate)
                koncFrejm = self.citac.get_sirovi(kanal, dan)
                zeroFrejm, spanFrejm = self.citac.get_zero_span(kanal, dan, 1)
                # append dnevne frejmove na glavni ako imaju podatke
                if len(koncFrejm):
                    masterKoncFrejm = masterKoncFrejm.append(koncFrejm)
                if len(zeroFrejm):
                    masterZeroFrejm = masterZeroFrejm.append(zeroFrejm)
                if len(spanFrejm):
                    masterSpanFrejm = masterSpanFrejm.append(spanFrejm)
                # advance progress bar
                self.progressbar.setValue(d)
            # zatvori progres bar nakon ucitavanja svih dana
            self.progressbar.close()
            del self.progressbar #manualno izbriši progress bar nakon kraja
            # drop dupliciranih indeksa
            masterKoncFrejm = masterKoncFrejm[~masterKoncFrejm.index.duplicated()]
            masterSpanFrejm = masterSpanFrejm[~masterSpanFrejm.index.duplicated()]
            masterZeroFrejm = masterZeroFrejm[~masterZeroFrejm.index.duplicated()]
            # od ,do moramo pretvoiti u datetime.date objekte
            od = datetime.datetime.strptime(od.toString(QtCore.Qt.ISODate), "%Y-%m-%d").date()
            do = datetime.datetime.strptime(do.toString(QtCore.Qt.ISODate), "%Y-%m-%d").date()
            # dohvati broj podataka u satu
            try:
                frek = int(np.floor(60/self.citac.get_broj_u_satu(kanal)))
            except Exception as err:
                logging.error(str(err), exc_info=True)
                # default na minutni period
                frek = -1
            if frek <= 1:
                frek = 'Min'
                start = datetime.datetime.combine(od, datetime.time(0, 1, 0))
                kraj = do + datetime.timedelta(1)
            else:
                frek = str(frek) + 'Min'
                start = datetime.datetime.combine(od, datetime.time(0, 0, 0))
                kraj = do + datetime.timedelta(1)
            # generiamo novi time raspon prema ocekivanom rasponu i frekfenciji uzorkovanja
            fullraspon = pd.date_range(start=start, end=kraj, freq=frek)
            # reindex koncentracijski data zbog rupa u podacima (ako nedostaju rubni podaci)
            masterKoncFrejm = masterKoncFrejm.reindex(fullraspon)
            # sredi satuse missing podataka
            masterKoncFrejm = self.sredi_missing_podatke(masterKoncFrejm)
            # output frejmove
            return masterKoncFrejm, masterZeroFrejm, masterSpanFrejm
        except Exception as err:
            # slucaj pogreške prilikom rada
            logging.error(str(err), exc_info=True)
            # potrebno je ugasiti progressbar ako postoji
            if hasattr(self, 'progressbar'):
                self.progressbar.close()
                del self.progressbar
            # reraise pogresku koju smo presreli
            raise Exception('Problem kod ucitavanja podataka') from err

    def sredi_missing_podatke(self, frejm):
        # indeks svi konc nan
        frejm['koncentracija'] = frejm['koncentracija'].astype(np.float64)
        frejm['status'] = frejm['status'].astype(np.float64)
        i0 = np.isnan(frejm['koncentracija'])
        # indeks konc i status su nan
        i1 = (np.isnan(frejm['koncentracija']))&(np.isnan(frejm['status']))
        # indeks konc je nan, status nije
        i2 = (np.isnan(frejm['koncentracija']))&([not m for m in np.isnan(frejm['status'])])

        frejm.loc[i1, 'status'] = self.NEDOSTAJE
        frejm.loc[i2, 'status'] = [self._bor_value(m, self.NEDOSTAJE) for m in frejm.loc[i2, 'status']]
        frejm.loc[i0, 'flag'] = False #za sve nan koncentracije flag je loš
        return frejm

    def _bor_value(self, status, val):
        """
        binary OR operation -- adding missing status
        """
        try:
            return int(status) | int(val)
        except Exception:
            return self.NEDOSTAJE
