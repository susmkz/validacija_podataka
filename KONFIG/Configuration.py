#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import configparser
import matplotlib.colors as colors


class MainKonfig(object):
    """
    Klasa za glavni konfiguracijski objekt aplikacije.
    Klasa zadužena za čitanje opcija iz konfig file-a (logging, REST, ...)
    """
    def __init__(self):
        """Konstruktor klase"""
        # mapa za dekodiranje nivoa logginga
        self.LOG_LEVELS = {
            'DEBUG': logging.DEBUG,
            'INFO':logging.INFO,
            'WARNING':logging.WARNING,
            'ERROR':logging.ERROR,
            'CRITICAL':logging.CRITICAL}
        # konfigparser objekt
        self.cfg = configparser.ConfigParser()

    def read_konfig_file(self, filename):
        """
        Funkcija koja čita neki konfiguracijski file
        """
        self.cfg.read(filename)

    def save_konfig_file(self, filename):
        """
        Funkcija koja sprema podatke u novi konfiguracijski file (filename)
        """
        with open(filename, mode='w') as f:
            self.cfg.write(f)

    def get_konfig_option(self, section, option, fallback):
        """
        Funkcija vraća podatak pod grupom ("section"), naziva opcije ("option"). U slučaju da
        zadana grupa ili naziv opcije ne postoje, vraćamo "fallback" vrijednost
        """
        out = self.cfg.get(section, option, fallback=fallback)
        # definiranje boja zahtjeva malo posla
        if option in ['linecolor', 'markerfacecolor', 'markeredgecolor']:
            if "#" in out:
                # pretvori boju iz hex zapisa
                return colors.hex2color(out)
            else:
                # slucaj kada imamo rgb : (0, 0, 0)
                # čitamo sve kao string
                rgba = out.replace('(', '') # mičemo zagrade
                rgba = out.replace(')', '') # mičemo zagrade
                rgba = rgba.split(sep=',') # split stringa na elemente odvojene zarezima
                rgba = [float(i.strip()) for i in rgba] # za svaki element, strip whitespace i pretvori u float
                if len(rgba) in [3,4]:
                    # ako imamo 3 ili 4 člana, sve je OK, (rgb, rgba)
                    return tuple(rgba)
                else:
                    # krivo zadana boja, vrati fallback
                    return fallback
        elif option in ['markersize', 'linewidth']:
            # markersize i linewidth su floatovi - potrebno ih je pretvoriti
            return float(out)
        else:
            # vrati string iz konfiga
            return out

    def set_konfig_option(self, section, option, val):
        """
        Postavljanje nove vrijednosti ("val") pod neku grupu ("section") i naziv opcije ("option").
        """
        if not self.cfg.has_section(section):
            # ako grupa ne postoji, moramo ju stvoriti
            self.cfg.add_section(section)
        # postavljanje opcije
        self.cfg.set(section, option, value=str(val))

if __name__ == '__main__':
    konfig = MainKonfig()
