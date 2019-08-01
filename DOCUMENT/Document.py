#!/usr/bin/python3
# -*- coding: utf-8 -*-
from app.QTMODELS import TreeModel
from app.DOCUMENT.Session import Session


class Dokument(object):
    """
    Klasa za glavni dokument aplikacije.
    sadrzi:
    self._mjerenja --> mapa (dict) sa meta-podacima o mjerenjima (za sve kanale)
    self._treeModelMjerenja --> tree model sa podacima o mjerenjima (za izbor kanala)
    self._session --> trenutno aktivni session
    """
    def __init__(self):
        """Konstruktor klase"""
        self._mjerenja = {}
        self._treeModelMjerenja = TreeModel.ModelDrva()
        # stvori prazan session (podaci su {} -empty dict)
        self._session = Session({}, filename=None)

    @property
    def mjerenja(self):
        """Getter mape podataka o pojedinom kanalu, za sve dostupne kanale."""
        return self._mjerenja

    @mjerenja.setter
    def mjerenja(self, x):
        """
        Setter mape podataka o pojedinom kanalu, za sve dostupne kanale.
        Prilikom postavljanja moramo povezati bitne kanale i moramo updateati
        tree model programa mjerenja.
        """
        # zapamti mapu mjerenja
        self._mjerenja = x
        # povezi kanale (NOx i PM grupa)
        for kanal in self._mjerenja:
            pomocni = self._get_povezane_kanale(kanal)
            for i in pomocni:
                self._mjerenja[kanal]['povezaniKanali'].append(i)
            lista = sorted(self._mjerenja[kanal]['povezaniKanali'])
            self._mjerenja[kanal]['povezaniKanali'] = lista
        # sastavi tree model
        self._konstruiraj_tree_model()

    def provjeri_grupu_kanala(self, kanali):
        """
        Funkcija provjerava listu kanala, proverava svaki pojedini kanal te
        dodaje njegove povezane kanale na popis. Output je lista kanala (bez duplikata).
        Ova metoda pronalazi sve povezane kanale...

        npr. ako je netko izabrao samo NO sa Desinica, povezani kanali (NOx i NO2)
        bi se trebali dodati na popis.
        """
        out = set()
        for kanal in kanali:
            out.add(kanal) # dodaj sebe (kanal) u set
            povezani = self._get_povezane_kanale(kanal)
            for k in povezani:
                out.add(k)
        return list(out)

    def _get_povezane_kanale(self, kanal):
        """
        Za zadani kanal, ako je formula kanala unutar nekog od setova,
        vrati sve druge kanale na istoj postaji koji takodjer pripadaju istom
        setu (NOx i PM).

        npr. ako je izabrani kanal Desinic NO, funkcija vraca id mjerenja za
        NO2 i NOx sa Desinica (ako postoje)
        """
        setovi = [('NOx', 'NO', 'NO2'), ('PM10', 'PM1', 'PM2.5')]
        output = set()
        postaja = self._mjerenja[kanal]['postajaId']
        formula = self._mjerenja[kanal]['komponentaFormula']
        usporednoMjerenje = self._mjerenja[kanal]['usporednoMjerenje']
        ciljaniSet = None
        for kombinacija in setovi:
            if formula in kombinacija:
                ciljaniSet = kombinacija
                break
        # ako kanal ne pripada setu povezanih...
        if ciljaniSet == None:
            return output
        for programMjerenjaId in self._mjerenja:
            if self._mjerenja[programMjerenjaId]['postajaId'] == postaja and programMjerenjaId != kanal:
                if self._mjerenja[programMjerenjaId]['komponentaFormula'] in ciljaniSet:
                    # usporedno mjerenje se mora poklapati
                    if self._mjerenja[programMjerenjaId]['usporednoMjerenje'] == usporednoMjerenje:
                        output.add(programMjerenjaId)
        return output

    def _konstruiraj_tree_model(self):
        """
        Funkcija za konstrukciju tree modela iz mape sa mjerenjima
        """
        # definiramo korjeni čvor
        root = TreeModel.TreeItem(['stanice', None, None, None], parent=None)
        # za svaku individualnu stanicu napravi TreeItem objekt i dodaj ga na korjeni čvor
        stanice = []
        for programMjerenjaId in self._mjerenja:
            stanica = self._mjerenja[programMjerenjaId]['postajaNaziv']
            if stanica not in stanice:
                stanice.append(stanica)
        stanice = sorted(stanice) # sortiraj stanice po abecedi
        postaje = [TreeModel.TreeItem([name, None, None, None], parent=root) for name in stanice]
        # za svaki kanal napravi TreeItem objekt i dodaj ga na odgovarajucu postaju (čvor)
        for programMjerenjaId in self._mjerenja:
            stanica = self._mjerenja[programMjerenjaId]['postajaNaziv']
            komponenta = self._mjerenja[programMjerenjaId]['komponentaNaziv']
            formula = self._mjerenja[programMjerenjaId]['komponentaFormula']
            mjernaJedinica = self._mjerenja[programMjerenjaId]['komponentaMjernaJedinica']
            opis = " ".join([formula, '[', mjernaJedinica, ']'])
            usporedno = self._mjerenja[programMjerenjaId]['usporednoMjerenje']
            data = [komponenta, usporedno, programMjerenjaId, opis]
            redniBrojPostaje = stanice.index(stanica)
            # kreacija TreeItem objekta
            TreeModel.TreeItem(data, parent=postaje[redniBrojPostaje])
        # postavljanje root itema (sadrzi sve grane i listove (čvorove) u sebi)
        self._treeModelMjerenja = TreeModel.ModelDrva(root=root)

    @property
    def treeModelProgramaMjerenja(self):
        """ Getter instance Qt tree modela za izbor kanala."""
        return self._treeModelMjerenja

    @property
    def session(self):
        """ Getter trenutno aktivnog Sessiona."""
        return self._session

    @property
    def sviKanali(self):
        """
        Vrati trenutni popis svih kanala u aktivnom Session-u.
        """
        return self._session.sviKanali

    def new_session(self, kanali):
        """
        Funkcija za stvaranje novog Session objekta nakon učitavanja sa REST-a.
        "kanali" je mapa koja definira sve potrebne podatke za rad Sessiona.
        kanali:
            -kanalId (key)
            -metaData (metapodaci za zadani kanalId)
            -status_code (int2string - decode mapa za statuse)
            -koncentracija frejm (dataframe podataka koncentracije)
            -zero frejm (dataframe podataka zero)
            -span frejm (dataframe podataka span)
            -korekcija frejm (frejm korekcijske tablice)
        """
        self._session = Session(kanali)

    def save_session(self, filename):
        """
        Funkcija koja sprema trenutnog sessiona u file.
        """
        self._session.save_to_file(filename)

    def load_session(self, filename):
        """
        Funkcija koja učitava Session iz filea.
        """
        self._session = Session({}, filename=filename)

    def get_kanal_datastore(self, kanal):
        """
        Funkcija vraća datastore iz aktivnog Session-a podključem 'kanal'
        """
        return self._session.get_datastore(kanal)
