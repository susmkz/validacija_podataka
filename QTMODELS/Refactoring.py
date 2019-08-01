#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Refactoring QT modela, imaju dosta zajedničkih funkcija -> izbjegavanje copy-paste koda
"""

#import copy
#import numpy as np
#import pandas as pd
#from PyQt5 import QtCore, QtGui


############ FUNCKIJE I PROPERTIES U MODELIMA ##################################
KONCENTRACIJA_STUFF = [
    "rowCount", "columnCount", "flags", "data", "headerData", "dataframe",
    "kanalId", "broj_u_satu", "status_code", "metaData", "unitConversionFactor",
    "postaja", "formula", "jedinica", "puniOpis", "opis", "povezaniKanali",
    "isNOx", "isPM", "get_nearest_row", "get_index_for_row", "_test_ispravnosti_korekcijske_tablice",
    "_pripremi_korekcijsku_tablicu", "_calc_ldl_values", "_modify_LDL_status_and_flags",
    "convert_units", "apply_correction", "change_user_flag", "get_flags_to_sync",
    "get_flags", "set_synced_flag", "set_logical_sync_flag", "_test_for_all_nan_range",
    "decode_status", "badFlagIndex", "goodFlagIndex", "badLDLIndex", "startTime",
    "endTime", "yPlotRange", "indeks", "ldl_line", "koncentracija_line",
    "korekcija_line", "koncentracijaOk", "koncentracijaBad", "korekcijaOk",
    "korekcijaBad", "get_korekcija_in_ppb", "get_pickle_map", "set_pickle_map"]

SATNI_STUFF = [
    "rowCount", "columnCount", "flags", "data", "headerData", "dataframe",
    "kanalId", "broj_u_satu", "status_code", "metaData", "unitConversionFactor",
    "postaja", "formula", "jedinica", "puniOpis", "opis", "povezaniKanali",
    "isNOx", "isPM", "get_nearest_row", "get_index_for_row", "_satni_agregator",
    "convert_units", "_binor_statuse", "_calc_mean", "_count_nan", "_calc_obuhvat",
    "_calc_valjan", "_test_for_all_nan_range", "get_valid_average", "get_valid_std",
    "get_valid_min", "get_valid_max", "get_valid_obuhvat", "decode_status",
    "badFlagIndex", "goodFlagIndex", "startTime", "endTime", "yPlotRange",
    "indeks", "koncentracija_line", "korekcija_line", "koncentracijaOk",
    "koncentracijaBad", "korekcijaOk", "korekcijaBad", "get_pickle_map", "set_pickle_map"]

ZEROSPAN_STUFF = [
    "rowCount", "columnCount", "flags", "data", "headerData", "tip", "dataframe",
    "kanalId", "broj_u_satu", "metaData", "unitConversionFactor", "postaja",
    "formula", "jedinica", "puniOpis", "opis", "povezaniKanali", "isNOx", "isPM",
    "_test_ispravnosti_korekcijske_tablice", "_pripremi_korekcijsku_tablicu",
    "_calc_ldl_values", "apply_correction", "initial_unit_conversion",
    "convert_units", "_test_for_all_nan_range", "indeks", "yPlotRange",
    "baseline", "maxAllowed", "minAllowed", "korekcija", "get_kriterij_ok",
    "get_kriterij_bad", "korekcijaOk", "korekcijaBad", "spanOk", "spanBad",
    "get_pickle_map", "set_pickle_map"]

KOREKCIJA_STUFF = [
    "rowCount", "columnCount", "flags", "data", "headerData", "setData", "sort",
    "insertRows", "removeRows", "dataframe", "kanalId", "metaData",
    "unitConversionFactor", "postaja", "formula", "jedinica", "puniOpis",
    "opis", "povezaniKanali", "isNOx", "isPM", "convert_units",
    "set_AB_for_row", "get_pickle_map", "set_pickle_map"]


################################################################################
class BaseModelMixin(object):
    """
    Mixin za osnovni dio modela (kanalId i metapodaci)
    - kanalId
    - metadata
    """
    def __init__(self):
        # kanal Id - ID programa mjerenja iz baze
        self._kanalId = None
        # mapa sa metapodacima kanala (formula, postaja, mjerna jedinica...)
        self._metaData = {}

    @property
    def kanalId(self):
        """Getter ID programa mjerenja (jedinstvena oznaka u bazi)."""
        return self._kanalId

    @kanalId.setter
    def kanalId(self, x):
        """Setter ID programa mjerenja (jedinstvena oznaka u bazi)."""
        self._kanalId = x

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
################################################################################

################################################################################
class StatusDecoderMixin(object):
    """
    Mixin za dekodiranje statusa
    """
    def __init__(self):
        # mapa sa bit/status podacima (za binarno kodiranje/dekodiranje statusa)
        self._status_int2str = {}
        self._status_str2int = {}
        # lookup mapa za vec "prevedene" statuse
        self._status_lookup = {}

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
################################################################################
