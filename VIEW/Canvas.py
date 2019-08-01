#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import functools
import datetime
import numpy as np
import pandas as pd
from PyQt5 import QtGui, QtCore, QtWidgets
import matplotlib
from distutils.version import LooseVersion #bitno za switch matplotlib verzije...preko 3.0 Legend.draggable je depreciated i javlja warning
from matplotlib import gridspec
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.widgets import SpanSelector

try:
    import matplotlib.backends.qt_editor.figureoptions as figureoptions
except ImportError as err:
    logging.error(str(err), exc_info=True)
    figureoptions = None


def semirandom_styles():
    """
    Generator stilova za graf, prvih par je predodređeno, ostali su random.
    Ideja je "zip" kanala i generatora da bi stvoriti konačni iterator stilova.
    Oprez prilikom koristenja, jer unutar generatora je infinite loop. Zip staje
    čim se potrosi jedan iterator dakle zip za konačnom listom je safe.
    """
    linestlyes = ['-', '-.', ':']
    yield ('-', (0.0,0.0,0.2))
    yield ('-', (0.1,0.0,0.4))
    yield ('-', (0.0,0.1,0.6))
    yield ('-', (0.1,0.1,0.8))
    while True:
        yield (np.random.choice(linestlyes), tuple(np.random.random(size=3)))


class MyPlotNavigation(NavigationToolbar):
    """
    SUBKLASA NAVIGATION TOOLBARA... ACCESS DO _ MEMBERA JE PROBLEM!
    PITANJE VREMENA KADA SE SE SLOMITI (možda sa idućom verzijom matplotlib paketa ili nikad).

    Ako netko smisli nesto pametnije, slobodno promjenite na bolje.
    Problem je u pristupu "private" varijabli "self._actions" koja definira koji su
    alati navigacijskog toolbara u upotrebi ('zoom', 'pan', ...) i overload funkcije
    "_update_buttons_checked". Sve varijable sa _ su podložne promjeni implementacije ili
    naziva bez upozorenja.

    -dodan je custom signal : signal_tools_in_use
        - cilj je signalizirati kada je aktivan tool za PAN ili ZOOM
        - kanvas hvata taj signal sa ciljem uključivanja span selectora

    -funkcija "_update_buttons_checked" je overloadana
        -cilj je samo naknadno emitirati signal (gore opisan) koji javlja da li
        se trenutno koriste alati PAN i ZOOM
    """
    # definiramo signal koji javlja da li su aktivni alati pan ili zoom
    signal_tools_in_use = QtCore.pyqtSignal(bool) #True ako su pan i zoom aktivni

    def __init__(self, kanvas, parent):
        """Konstruktor klase"""
        super(MyPlotNavigation, self).__init__(kanvas, parent)

    def _update_buttons_checked(self):
        """
        Overloaded function. U biti je copy paste postojeće funkcije sa dodatnim
        djelom za signaliziranje alata u upotrebi.
        """
        # copy paste dio...
        self._actions['pan'].setChecked(self._active == 'PAN')
        self._actions['zoom'].setChecked(self._active == 'ZOOM')
        # dodatak za signalizaciju
        test = ((self._active == 'PAN') or (self._active == 'ZOOM'))
        # emitiraj signal
        self.signal_tools_in_use.emit(test)


class Kanvas(FigureCanvas):
    """
    Klasa koja definira kanvas (prostor za crtanje grafova).
    """
    # definiramo signal za promjenu flaga, int->kanal, str->str vrijeme u ISO formatu, bool->OK ili BAD
    signal_flag_change = QtCore.pyqtSignal(int, str, str, bool)
    #definiramo signal za izbor redka (zoom na tablicama sa podacima) -- pandas datetime
    signal_time_pick = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, parent=None, width=12, height=6, dpi=100):
        """
        Konstruktor klase. Sadrži 4 grafa na jednom kanvasu. Redom od gore prema
        dolje : span, zero, satni average koncentracija, koncentracija.
        """
        # definicija figure i kanvasa (inicijalizacija objekata)
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.fig)
        FigureCanvas.setSizePolicy(
            self,
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)
        # u principu parent će se automatski postaviti prilikom layout managementa
        self.setParent(parent)
        # status ostalih alata sa Navigation toolbara
        self.OTHER_TOOLS_IN_USE = False
        # Session - podaci koje treba crtati
        self.SESSION = None
        # Kanal u fokusu
        self.AKTIVNI_KANAL = None
        # memberi koji drze vrijeme za promjenu flaga -> vrijeme od-do
        self.__lastTimeMin = None
        self.__lastTimeMax = None
        # info koji je graf u fokusu (ostali su smanjeni)
        self.SPAN_IN_FOCUS = False
        self.ZERO_IN_FOCUS = False
        self.CONC_SATNI_IN_FOCUS = False
        self.CONC_IN_FOCUS = True
        # info o statusu legende i grida (da li ih crtamo)
        self.isLegendDrawn = False
        self.isGridDrawn = False
        # STYLE GENERATOR
        self.styleGenerator = semirandom_styles()
        # ostali pomocni plotovi (grafovi ostalih kanala)
        self.ostaliGrafovi = {}
        # gridspec layout subplotova - nacin na koji su grafovi poslagani na kanvasu
        self.gs = gridspec.GridSpec(4, 1, height_ratios=[1,1,1,4])
        # defiincija pojedinih osi subplotova
        self.axesConc = self.fig.add_subplot(self.gs[3, 0]) #koncentracija
        self.axesConcSatni = self.fig.add_subplot(self.gs[2, 0], sharex=self.axesConc) #koncentracija - satni aggregate
        self.axesSpan = self.fig.add_subplot(self.gs[0, 0], sharex=self.axesConc) #span
        self.axesZero = self.fig.add_subplot(self.gs[1, 0], sharex=self.axesConc) #zero
        # custom names TODO! za naziv plotova?
        self.axesConc._CUSTOM_NAME = 'Graf koncentracija'
        self.axesConcSatni._CUSTOM_NAME = 'Graf koncentracija - satni'
        self.axesZero._CUSTOM_NAME = 'Graf zero'
        self.axesSpan._CUSTOM_NAME = 'Graf span'
        # svi grafovi djele x os, skrivanje labela i tickova za sve osim koncentracijskog grafa
        self.axesSpan.xaxis.set_visible(False)
        self.axesZero.xaxis.set_visible(False)
        self.axesConcSatni.xaxis.set_visible(False)
        # prebaci tickove na "staggered" nacin radi citljivosti (prebacivanje tickova desno)
        self.axesSpan.yaxis.tick_right()
        self.axesConcSatni.yaxis.tick_right()
        #prebaci y labele na "staggered" nacin radi citljivosti (prebacivanje labela desno)
        self.axesSpan.yaxis.set_label_position("right")
        self.axesConcSatni.yaxis.set_label_position("right")
        # podesi spacing izmedju axesa (sljepi grafove radi ustede vertikalnog prostora)
        self.fig.subplots_adjust(wspace=0.001, hspace=0.001)
        # update geometriju
        FigureCanvas.updateGeometry(self)
        # definiramo "custom" kontekstni meni na desni klik
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # span selektori za kanvase - promjena flaga
        self.spanSelector = SpanSelector(self.axesConc,
                                         self.spanSelectorConcCallback,
                                         direction='horizontal',
                                         button=1,
                                         useblit=True,
                                         rectprops=dict(alpha=0.2, facecolor='yellow'))
        self.spanSelectorSatni = SpanSelector(self.axesConcSatni,
                                              self.spanSelectorConcSatniCallback,
                                              direction='horizontal',
                                              button=1,
                                              useblit=True,
                                              rectprops=dict(alpha=0.2, facecolor='yellow'))
        # definiranje callback-a za pick evente
        self.pickCid = self.mpl_connect('button_press_event', self.on_pick)

    def promjeni_aktivni_kanal(self, x, draw=True):
        """
        Promjena aktivnog kanala (x) za crtanje. Dodatna opcija "draw" služi kao parametar koji
        forsira ponovno crtanje grafa.
        """
        # nema smisla mjenjati ako je x već postavljen kao aktivni kanal
        if x != self.AKTIVNI_KANAL:
            self.AKTIVNI_KANAL = x
        # force redraw
        if draw:
            self.crtaj(noviSession=False)

    def nav_tools_in_use(self, x):
        """
        Callback za status aktivnih alata u navigation toolbaru. Ako se koriste
        navigacijski alati za pan i zoom, moram iskljuciti span selector na grafovima.
        """
        self.OTHER_TOOLS_IN_USE = x
        self.spanSelector.set_visible(not x)
        self.spanSelectorSatni.set_visible(not x)

    def on_pick(self, event):
        """
        Pick event za interakciju sa kanvasom. Event sadrži informacije koji graf je 'kliknut',
        koji gumb na mišu je aktivan, poziciju klika...
        """
        # event mora biti unutar osi te alati moraju biti ugaseni
        if ((not self.OTHER_TOOLS_IN_USE) and (event.inaxes in [self.axesConc, self.axesConcSatni, self.axesSpan, self.axesZero])):
            # potrebno je odrediti orgin os gdje moramo prikazati menu
            if event.inaxes == self.axesConcSatni:
                origin = 'satni'
            elif event.inaxes == self.axesConc:
                origin = 'koncentracija'
            else:
                origin = 'zero ili span'
            if event.button == 1:
                # left click
                # matplotlib conversion of xdata to pandas.datetime
                if origin in ['satni', 'koncentracija']:
                    # priprema vremena (round i prilagodba za tablicu)
                    tajm = self.num2date_converter(event.xdata, origin=origin)
                    # emit signal za izbor reda (prema vremenu)
                    self.signal_time_pick.emit(tajm)
            elif event.button == 3:
                # right click
                pos = QtGui.QCursor.pos()
                # matplotlib conversion of xdata to pandas.datetime
                if origin == 'satni':
                    # pomak vremena mora biti OK za satno agregirane...
                    tmin = self._mpltime_to_pdtime(event.xdata) - datetime.timedelta(hours=1)
                    tmax = self._mpltime_to_pdtime(event.xdata)
                    self.show_context_menu(pos, tmin, tmax, origin=origin)
                elif origin == 'koncentracija':
                    tmin = self._mpltime_to_pdtime(event.xdata)
                    tmax = self._mpltime_to_pdtime(event.xdata)
                    self.show_context_menu(pos, tmin, tmax, origin=origin)
                else:
                    # zero i span grafovi imaju jednostavniji kontekstni menu, vrijeme im nije potrebno
                    self.show_context_menu(pos, None, None, origin=origin)
            else:
                pass

    def _mpltime_to_pdtime(self, x):
        """Converter iz matplotlib date (broj) u pandas datetime"""
        xpoint = matplotlib.dates.num2date(x) #datetime.datetime
        #problem.. rounding offset aware i offset naive datetimes..workaround
        xpoint = datetime.datetime(xpoint.year,
                                   xpoint.month,
                                   xpoint.day,
                                   xpoint.hour,
                                   xpoint.minute,
                                   xpoint.second)
        #konverzija iz datetime.datetime objekta u pandas.tislib.Timestamp
        xpoint = pd.to_datetime(xpoint)
        return xpoint

    def num2date_converter(self, x, origin='koncentracija'):
        """
        Pretvara matplotlib datum (broj) u pandas timestamp. Zaokruživanje vremena ovisi o
        tipu grafa (satno ili minutno zaokruživanje.)
        """
        # pretvori u timestamp
        tajm = self._mpltime_to_pdtime(x)
        # zaokruži
        if origin == 'koncentracija':
            return tajm.round('Min')
        elif origin == 'satni':
            return tajm.round('H')
        else:
            raise ValueError('wrong interval')

    def spanSelectorConcCallback(self, low, high):
        """
        Span selector callback za koncentracije.
        """
        if low != high:
            pos = QtGui.QCursor.pos()
            self.span_select_context_menu(pos, low, high, origin='koncentracija')

    def spanSelectorConcSatniCallback(self, low, high):
        """
        Span selector callback za satno agregirane koncentracije.
        """
        if low != high:
            pos = QtGui.QCursor.pos()
            self.span_select_context_menu(pos, low, high, origin='satni')

    def set_axes_focus(self, tip='koncentracija'):
        """
        Prebacivanje fokusa izmedju grafova za span-zero-satno agregirane-koncentracije
        """
        if tip == 'span':
            self.gs.set_height_ratios([4,1,1,1])
            self.SPAN_IN_FOCUS = True
            self.ZERO_IN_FOCUS = False
            self.CONC_SATNI_IN_FOCUS = False
            self.CONC_IN_FOCUS = False
        elif tip == 'zero':
            self.gs.set_height_ratios([1,4,1,1])
            self.SPAN_IN_FOCUS = False
            self.ZERO_IN_FOCUS = True
            self.CONC_SATNI_IN_FOCUS = False
            self.CONC_IN_FOCUS = False
        elif tip == 'satni':
            self.gs.set_height_ratios([1,1,4,1])
            self.SPAN_IN_FOCUS = False
            self.ZERO_IN_FOCUS = False
            self.CONC_SATNI_IN_FOCUS =True
            self.CONC_IN_FOCUS = False
        else:
            #koncentracije (minutna rezolucija)
            self.gs.set_height_ratios([1,1,1,4])
            self.SPAN_IN_FOCUS = False
            self.ZERO_IN_FOCUS = False
            self.CONC_SATNI_IN_FOCUS = False
            self.CONC_IN_FOCUS = True
        self.fig.tight_layout()
        # podesi razmak između grafova (sljepi grafove)
        self.fig.subplots_adjust(wspace=0.001, hspace=0.001)
        self.draw()
        self.crtaj_legendu(self.isLegendDrawn, skipDraw=True)
        self.crtaj_grid(self.isGridDrawn, skipDraw=False)

    def promjena_flaga(self, flag=True):
        """
        Metoda sluzi za signaliziranje promjene flaga.
        """
        self.signal_flag_change.emit(self.AKTIVNI_KANAL, self.__lastTimeMin, self.__lastTimeMax, flag)

    def span_select_context_menu(self, pos, tmin, tmax, origin='satni'):
        """
        Prikaz menua za promjenu flaga uz span select. Za satni origin min vrijeme moramo
        pomaknuti dovoljno unazad da uhvati dobar period agregiranja.

        pos - pozicija gdje prikazujemo menu
        tmin - vrijeme od
        tmax - vrijeme do
        origin - graf koji je pokrenuo event
        """
        # pretvori u pandas timestamp
        tmin = self._mpltime_to_pdtime(tmin)
        tmax = self._mpltime_to_pdtime(tmax)
        # zapamti rubna vremena intervala, trebati ce za druge metode
        if origin == 'satni':
            # makni sat unazad 1 sat
            minsat = pd.to_datetime(tmin - datetime.timedelta(hours=1))
            self.__lastTimeMin = str(minsat)
            self.__lastTimeMax = str(tmax)
        else:
            self.__lastTimeMin = str(tmin)
            self.__lastTimeMax = str(tmax)

        # stvaramo menu za prikaz
        menu = QtWidgets.QMenu(self)
        menu.setTitle('Menu')
        # definiramo akcije
        action1 = QtWidgets.QAction("Flag: dobar", menu)
        action2 = QtWidgets.QAction("Flag: los", menu)
        # dodajemo akcije u menu
        menu.addAction(action1)
        menu.addAction(action2)
        # povezujemo akcije sa callbackovima
        action1.triggered.connect(functools.partial(self.promjena_flaga, flag=True))
        action2.triggered.connect(functools.partial(self.promjena_flaga, flag=False))
        # prikaz menu-a
        menu.popup(pos)

    def show_context_menu(self, pos, tmin, tmax, origin='satni'):
        """
        Right click kontekstni menu. Za origin == 'satni' vrijeme moramo
        pomaknuti da uhvatimo dobar period za promjenu flaga. Za origin==koncentracija
        vrijeme je dobro definirano.

        pos - pozicija gdje prikazujemo menu
        tmin - vrijeme od
        tmax - vrijeme do
        origin - graf koji je pokrenuo event
        """
        # zapamti vremena... trebati će za flag change
        self.__lastTimeMin = tmin
        self.__lastTimeMax = tmax
        # definiraj menu
        menu = QtWidgets.QMenu(self)
        menu.setTitle('Menu')
        # definiranje akcija
        if origin in ['satni', 'koncentracija']:
            action1 = QtWidgets.QAction("Flag: dobar", menu)
            action2 = QtWidgets.QAction("Flag: los", menu)
        action3 = QtWidgets.QAction("focus: SPAN", menu)
        action3.setCheckable(True)
        action3.setChecked(self.SPAN_IN_FOCUS)
        action4 = QtWidgets.QAction("focus: ZERO", menu)
        action4.setCheckable(True)
        action4.setChecked(self.ZERO_IN_FOCUS)
        action5 = QtWidgets.QAction("focus: satno agregirani", menu)
        action5.setCheckable(True)
        action5.setChecked(self.CONC_SATNI_IN_FOCUS)
        action6 = QtWidgets.QAction("focus: koncentracija", menu)
        action6.setCheckable(True)
        action6.setChecked(self.CONC_IN_FOCUS)
        action7 = QtWidgets.QAction("Legend", menu)
        action7.setCheckable(True)
        action7.setChecked(self.isLegendDrawn)
        action8 = QtWidgets.QAction("Grid", menu)
        action8.setCheckable(True)
        action8.setChecked(self.isGridDrawn)
        # slaganje akcija u menu
        if origin in ['satni', 'koncentracija']:
            menu.addAction(action1)
            menu.addAction(action2)
            menu.addSeparator()
        menu.addAction(action3)
        menu.addAction(action4)
        menu.addAction(action5)
        menu.addAction(action6)
        menu.addSeparator()
        menu.addAction(action7)
        menu.addAction(action8)
        # povezi akcije menua sa callback funkcijama
        if origin in ['satni', 'koncentracija']:
            action1.triggered.connect(functools.partial(self.promjena_flaga, flag=True))
            action2.triggered.connect(functools.partial(self.promjena_flaga, flag=False))
        action3.triggered.connect(functools.partial(self.set_axes_focus, tip='span'))
        action4.triggered.connect(functools.partial(self.set_axes_focus, tip='zero'))
        action5.triggered.connect(functools.partial(self.set_axes_focus, tip='satni'))
        action6.triggered.connect(functools.partial(self.set_axes_focus, tip='koncentracija'))
        action7.triggered.connect(self.crtaj_legendu)
        action8.triggered.connect(self.crtaj_grid)
        # pokazi menu na poziciji pos
        menu.popup(pos)

    def set_session(self, x):
        """
        Connect Sessiona sa kanvasom... cilj je prosljediti pointer na trenutni session
        kanvasu kako bi metode za crtanje mogle doci do trenutnih podataka.
        """
        # postavi novi Session
        self.SESSION = x
        # pozovi crtanje
        self.crtaj(noviSession=True)

    def crtaj(self, noviSession=True):
        """
        Glavna metoda za crtanje podataka na svim grafovima.

        noviSession - ako je True, ponistava se prethodni "zoom" te se slika crta
        zoomirana na granice ucitanog podrucja. To je slucaj kada stavljamo novi
        session u kanvas. Inače ponovno crtanje unutar prethodno zapamćenih granica.
        """
        #TODO! spremanje nekih opcija grafova nakon crtanja?
        # zapamti prethodne limite grafa
        self.zapamti_trenutni_zoom()
        # clear sve osi
        self.clear_graf()
        # delegacija crtanja pojedinim grafovima
        self.crtaj_zero_span(tip='zero')
        self.crtaj_zero_span(tip='span')
        self.crtaj_koncentracija()
        self.crtaj_satne()
        # rotacija labela x osi najnižeg grafa radi čitljivosti
        allXLabels = self.axesConc.get_xticklabels()
        for label in allXLabels:
            label.set_rotation(30)
            label.set_fontsize(8)

        if noviSession:
            # ako je novi session, postavi default granice kao max raspon podataka
            self.default_trenutni_zoom()
        else:
            # ako crtamo već postojeći session, zoomiraj na prethodno zapamćeni zoom
            self.restore_trenutni_zoom()
        # kompresija prostora za crtanje - maksimiziramo prostor koji imamo na raspolaganju
        self.fig.tight_layout()
        # podesi spacing izmedju grafova (sljepi grafove)
        self.fig.subplots_adjust(wspace=0.001, hspace=0.001)
        self.draw() #naredba kanvasu za render
        self.crtaj_legendu(self.isLegendDrawn, skipDraw=True)
        self.crtaj_grid(self.isGridDrawn, skipDraw=False)
        # zapamti limite grafa nakon sto je nacrtan za buduće crtanje
        self.zapamti_trenutni_zoom()

    def zapamti_trenutni_zoom(self):
        """
        Funkcija pamti x i y raspone na svim grafovima. Cilj je prilikom promjene imati
        isti zoom level.
        """
        # ostali grafovi imaju synced x osi sa grafom koncentracije, nema smisla ih pamtiti
        self.ZOOM_LEVEL_X = self.axesConc.get_xlim()
        self.ZOOM_LEVEL_CONC = self.axesConc.get_ylim()
        self.ZOOM_LEVEL_SATNI = self.axesConcSatni.get_ylim()
        self.ZOOM_LEVEL_ZERO = self.axesZero.get_ylim()
        self.ZOOM_LEVEL_SPAN = self.axesSpan.get_ylim()

    def restore_trenutni_zoom(self):
        """
        Funkcija postavlja x i y raspone na svim grafovima koji su prethodno zapamceni.
        """
        # ostali grafovi imaju synced x osi sa grafom koncentracije, nema smisla ih pamtiti
        self.axesConc.set_xlim(self.ZOOM_LEVEL_X)
        self.axesConc.set_ylim(self.ZOOM_LEVEL_CONC)
        self.axesConcSatni.set_ylim(self.ZOOM_LEVEL_SATNI)
        self.axesZero.set_ylim(self.ZOOM_LEVEL_ZERO)
        self.axesSpan.set_ylim(self.ZOOM_LEVEL_SPAN)

    def default_trenutni_zoom(self):
        """
        Funkcija postavlja defaultne x i y raspone na svim grafovima prilikom prvog crtanja.
        """
        #default x raspon
        datastore = self.SESSION.get_datastore(self.AKTIVNI_KANAL)
        xmin = matplotlib.dates.date2num(datastore.koncentracija.startTime - datetime.timedelta(hours=1))
        xmax = matplotlib.dates.date2num(datastore.koncentracija.endTime + datetime.timedelta(hours=1))
        self.ZOOM_LEVEL_X = (xmin, xmax)
        #default y rasponi
        lowKonc = min([self.SESSION.get_datastore(kanal).koncentracija.yPlotRange[0] for kanal in self.SESSION.sviKanali])
        highKonc = max([self.SESSION.get_datastore(kanal).koncentracija.yPlotRange[1] for kanal in self.SESSION.sviKanali])
        self.ZOOM_LEVEL_CONC = (lowKonc, highKonc)
        lowSatni = min([self.SESSION.get_datastore(kanal).satni.yPlotRange[0] for kanal in self.SESSION.sviKanali])
        highSatni = max([self.SESSION.get_datastore(kanal).satni.yPlotRange[1] for kanal in self.SESSION.sviKanali])
        self.ZOOM_LEVEL_SATNI = (lowSatni, highSatni)
        lowZero = min([self.SESSION.get_datastore(kanal).zero.yPlotRange[0] for kanal in self.SESSION.sviKanali])
        highZero = max([self.SESSION.get_datastore(kanal).zero.yPlotRange[1] for kanal in self.SESSION.sviKanali])
        self.ZOOM_LEVEL_ZERO = (lowZero, highZero)
        lowSpan = min([self.SESSION.get_datastore(kanal).span.yPlotRange[0] for kanal in self.SESSION.sviKanali])
        highSpan = max([self.SESSION.get_datastore(kanal).span.yPlotRange[1] for kanal in self.SESSION.sviKanali])
        self.ZOOM_LEVEL_SPAN = (lowSpan, highSpan)
        #postavi nove granice zoom-a
        self.restore_trenutni_zoom()

    def clear_graf(self):
        """
        Clear svih grafova. Brišemo mapu sa linijama ostalih kanala, clearamo sve
        grafove.
        """
        #TODO!
        self.ostaliGrafovi = {}
        self.blockSignals(True)
        self.axesConc.clear()
        self.axesConcSatni.clear()
        self.axesSpan.clear()
        self.axesZero.clear()
        self.blockSignals(False)

    def crtaj_legendu(self, toggle, skipDraw=False):
        """
        Funkcija za crtanje / toggle legende. "toggle" je state legende, ako je True onda crtamo.
        "skipDraw" služi da preskočimo korak za render (draw).
        """
        # zapamti status da li se crta legenda
        self.isLegendDrawn = toggle
        # all legends - iterator (axes, da li je fokus na tom axesu)
        ite = zip([self.axesConc, self.axesConcSatni, self.axesSpan, self.axesZero],
                  [self.CONC_IN_FOCUS, self.CONC_SATNI_IN_FOCUS, self.SPAN_IN_FOCUS, self.ZERO_IN_FOCUS])
        # crtamo odvojenu legendu za svaki graf, prikazujemo samo onu na aktivnom grafu
        for i, j in ite:
            i.legend(fontsize=8, loc='center left', bbox_to_anchor=(1, 0.5))
            # switch za draggable opciju legende, ovisi o verziji matplotliba
            if LooseVersion(matplotlib.__version__) >= LooseVersion('3.0.0'):
                i.get_legend().set_draggable(True)
            else:
                i.get_legend().draggable(state=True)
            stejt = toggle and j
            i.get_legend().set_visible(stejt)
        # display legendu
        if not skipDraw:
            self.draw()

    def crtaj_grid(self, toggle, skipDraw=False):
        """
        Funkcija za crtanje / toggle grida. "toggle" je state grida, ako je True onda crtamo.
        "skipDraw" služi da preskočimo korak za render (draw).
        """
        self.isGridDrawn = toggle
        if toggle:
            for i in [self.axesConc, self.axesConcSatni, self.axesSpan, self.axesZero]:
                i.grid(which='major', color='black', linestyle='-',
                       linewidth='0.4', alpha=0.4)
                #minor tick lines?
                #i.grid(which='minor', color='black', linestyle='-',
                #       linewidth='0.2', alpha=0.2)
                #i.minorticks_on()
        else:
            for i in [self.axesConc, self.axesConcSatni, self.axesSpan, self.axesZero]:
                i.grid(False)
                #i.minorticks_off()
        if not skipDraw:
            self.draw()

    def crtaj_zero_span(self, tip='zero'):
        """
        Funkcija koja crta zero ili span graf (ovisno o parametru "tip")
        tip : 'zero', 'span'
        """
        try:
            # potreban nam je datastore aktivnog kanala da bi došli do podataka
            datastore = self.SESSION.get_datastore(self.AKTIVNI_KANAL)
            if tip == 'span':
                plotAxes = self.axesSpan # dinamički definiramo na koji graf crtamo
                indeks = datastore.span.indeks # indeks - podaci x osi
                gornjaGranica = datastore.span.maxAllowed # max dozvoljeno
                donjaGranica = datastore.span.minAllowed # min dozvoljeno
                spanLinija = datastore.span.baseline # osnovna linija
                korekcija = datastore.span.korekcija # osnovna linija korekcije
                okKorekcija = datastore.span.korekcijaOk # mjesta gdje je korekcija OK
                badKorekcija = datastore.span.korekcijaBad #mjesta gdje je korekcije loša
            elif tip == 'zero':
                plotAxes = self.axesZero # dinamički definiramo na koji graf crtamo
                indeks = datastore.zero.indeks # indeks - podaci x osi
                gornjaGranica = datastore.zero.maxAllowed # max dozvoljeno
                donjaGranica = datastore.zero.minAllowed # min dozvoljeno
                spanLinija = datastore.zero.baseline # osnovna linija
                korekcija = datastore.zero.korekcija # osnovna linija korekcije
                okKorekcija = datastore.zero.korekcijaOk # mjesta gdje je korekcija OK
                badKorekcija = datastore.zero.korekcijaBad #mjesta gdje je korekcije loša
            else:
                # nešto stvarno mora poći po zlu da dođemo do ove linije...
                raise ValueError("Only 'zero' or 'span' allowed")
            # PLOTTING
            # gornja granica
            self.spanTopLimit, = plotAxes.plot(
                indeks,
                gornjaGranica,
                label='Gornja granica',
                linestyle='--',
                linewidth=1.2,
                color='red')
            # donja granica
            self.spanLowLimit, = plotAxes.plot(
                indeks,
                donjaGranica,
                label='Donja granica',
                linestyle='--',
                linewidth=1.2,
                color='red')
            # originalna linija
            self.spanLine, = plotAxes.plot(
                indeks,
                spanLinija,
                label='Span',
                linestyle='-.',
                linewidth=1.0,
                color='blue')
            # linija nakon korekcije
            self.spanKorekcija, = plotAxes.plot(
                indeks,
                korekcija,
                label='Korekcija',
                linestyle='-',
                drawstyle='default',
                linewidth=1.2,
                color='black')
            #ok tocke (markeri) nakon korekcije
            self.spanGood, = plotAxes.plot(
                indeks,
                okKorekcija,
                label='Dobar span',
                linestyle='None',
                marker='d',
                markersize=6,
                markerfacecolor='green',
                markeredgecolor='green')
            #lose tocke (markeri) nakon korekcije
            self.spanBad, = plotAxes.plot(
                indeks,
                badKorekcija,
                label='Los span',
                linestyle='None',
                marker='d',
                markersize=6,
                markerfacecolor='red',
                markeredgecolor='red')
            # postavi y label - mjerna jedinica aktivne komponente
            if tip == 'zero':
                lab = 'ZERO '+datastore.zero.jedinica
                plotAxes.set_ylabel(lab)
            else:
                lab = 'SPAN '+datastore.span.jedinica
                plotAxes.set_ylabel(lab)
        except Exception as err:
            # slučaj kada dođe do pogreške u crtanju?
            logging.error(str(err), exc_info=True)

    def crtaj_koncentracija(self):
        """
        Crtanje podataka sa minutnim koncentracijama.
        """
        try:
            # potreban nam je datastore aktivnog kanala da bi došli do podataka
            datastore = self.SESSION.get_datastore(self.AKTIVNI_KANAL)
            indeks = datastore.koncentracija.indeks # x os
            lineLDL = datastore.koncentracija.ldl_line # LDL linija
            lineSviOK = datastore.koncentracija.koncentracijaOk # linija sa ok sirovim koncentracijama
            lineSviBAD = datastore.koncentracija.koncentracijaBad # linija sa bad sirovim koncentracijama
            lineOKkorekcija = datastore.koncentracija.korekcijaOk # linija sa podacima OK korekcije
            lineBadkorekcija = datastore.koncentracija.korekcijaBad # linija sa podacima loše korekcije
            glavniOpis = datastore.koncentracija.puniOpis # opis - za labele
            # PLOTTING
            # zero linija
            zeroLinija = self.axesConc.axhline(
                0.0,
                label='0 line',
                linewidth=0.9,
                color='black')
            # limit podataka -> najmanji vremenski indeks
            leftLimit = self.axesConc.axvline(
                datastore.koncentracija.startTime,
                label='Min vrijeme',
                linestyle='-.',
                linewidth=1.2,
                color='blue')
            # limit podataka -> najveci vremenski indeks
            rightLimit = self.axesConc.axvline(
                datastore.koncentracija.endTime,
                label='Max vrijeme',
                linestyle='-.',
                linewidth=1.2,
                color='blue')
            # LDL vrijednost
            self.koncLDL = self.axesConc.plot(
                indeks,
                lineLDL,
                label=glavniOpis+' - LDL',
                linestyle='-',
                linewidth=1.2,
                color='red')
            # zelena linija za sirove OK podatke
            self.koncLineOK, = self.axesConc.plot(
                indeks,
                lineSviOK,
                label=glavniOpis+' - sirovi OK',
                linestyle='-',
                linewidth=1.5,
                color='green')
            # crvena linija za sirove OK podatke
            self.koncLineBAD, = self.axesConc.plot(
                indeks,
                lineSviBAD,
                label=glavniOpis+' - sirovi BAD',
                linestyle='-',
                linewidth=1.5,
                color='red')
            # korekcijska linija OK - CRNA, puna debela linija
            self.koncKorekcijaOK, = self.axesConc.plot(
                indeks,
                lineOKkorekcija,
                label=glavniOpis+' - korekcija OK',
                linestyle='-',
                linewidth=1.5,
                color='black')
            # korekcijska linija BAD - CRNA, dotted debela linija
            self.koncKorekcijaBad, = self.axesConc.plot(
                indeks,
                lineBadkorekcija,
                label=glavniOpis+' - korekcija BAD',
                linestyle='-.',
                linewidth=1.5,
                color='black')
            # postavi y label - mjerna jedinica aktivne komponente
            lab = 'Konc. '+datastore.koncentracija.jedinica
            self.axesConc.set_ylabel(lab)
            # dohvati ostale kanale i plotaj i njih (spremi u pomocne radi on/off opcije)
            ostaliKanali = self.SESSION.get_ostale_kanale(self.AKTIVNI_KANAL)
            for k in ostaliKanali:
                self.crtaj_dodatni_kanal(k)
        except Exception as err:
            #pogreska prilikom crtanja?
            logging.error(str(err), exc_info=True)

    def crtaj_dodatni_kanal(self, tmpKanal):
        """Plot helper za crtanje dodatnog kanala."""
        self.styleGenerator = semirandom_styles() # reset style generator
        self.ostaliGrafovi[tmpKanal] = {}
        # generiranje seimirandom stila (prvih par je zadano...)
        linestil, tmpboja = self.styleGenerator.__next__() # manualno advancanje generatora
        # pristup podacima
        datastore = self.SESSION.get_datastore(tmpKanal)
        tmpOpis = datastore.koncentracija.puniOpis
        indeks = datastore.koncentracija.indeks
        fullline_korekcija = datastore.koncentracija.korekcija_line
        self.ostaliGrafovi[tmpKanal]['korekcija'], = self.axesConc.plot(
            indeks,
            fullline_korekcija,
            label=tmpOpis+' - korekcija',
            linestyle=linestil,
            linewidth=0.8,
            color=tmpboja,
            alpha=0.5)

    def crtaj_dodatni_kanal_satni(self, tmpKanal):
        """Plot helper za crtanje dodatnog kanala"""
        self.styleGenerator = semirandom_styles() #reset style generator
        self.ostaliGrafovi[tmpKanal] = {}
        #generiranje seimirandom stila (prvih par je zadano...)
        linestil, tmpboja = self.styleGenerator.__next__() # manualno advancanje generatora
        #pristup podacima
        datastore = self.SESSION.get_datastore(tmpKanal)
        tmpOpis = datastore.satni.puniOpis
        indeks = datastore.satni.indeks
        fullline_korekcija = datastore.satni.korekcija_line
        self.ostaliGrafovi[tmpKanal]['korekcija'], = self.axesConcSatni.plot(
            indeks,
            fullline_korekcija,
            label=tmpOpis+' - korekcija',
            linestyle=linestil,
            linewidth=0.8,
            color=tmpboja,
            alpha=0.5)

    def crtaj_satne(self):
        """
        Crtanje podataka sa satno agregiranim koncentracijama.
        """
        try:
            # potreban nam je datastore aktivnog kanala da bi došli do podataka
            datastore = self.SESSION.get_datastore(self.AKTIVNI_KANAL)
            indeks = datastore.satni.indeks # x os
            lineOriginalOK = datastore.satni.koncentracijaOk # linija sirovih koncentracija OK
            lineOriginalBAD = datastore.satni.koncentracijaBad # linija sirovih koncentracija BAD
            lineOKkorekcija = datastore.satni.korekcijaOk # linija gdje je korekcija OK
            lineBadkorekcija = datastore.satni.korekcijaBad # linija gdje je korekcija loša
            glavniOpis = datastore.satni.puniOpis # opis kanala za labele
            # vremena za start / kraj moraju odgovarati minutnim podacima
            startline = datastore.koncentracija.startTime
            endline = datastore.koncentracija.endTime
            # PLOTTING
            # zero linija ... orijentir
            zeroLinija = self.axesConcSatni.axhline(
                0.0,
                label='0 line',
                color='black')
            # limit podataka -> najmanji vremenski indeks
            leftLimit = self.axesConcSatni.axvline(
                startline,
                label='Min vrijeme',
                linestyle='-.',
                linewidth=1.2,
                color='blue')
            # limit podataka -> najveci vremenski indeks
            rightLimit = self.axesConcSatni.axvline(
                endline,
                label='Max vrijeme',
                linestyle='-.',
                linewidth=1.2,
                color='blue')
            # sve koncentracije koje su OK
            self.koncSatniGood, = self.axesConcSatni.plot(
                indeks,
                lineOriginalOK,
                label=glavniOpis+' - OK',
                linestyle='-',
                linewidth=1.5,
                color='green')
            # sve koncentracije koje su BAD
            self.koncSatniGood, = self.axesConcSatni.plot(
                indeks,
                lineOriginalBAD,
                label=glavniOpis+' - BAD',
                linestyle='-',
                linewidth=1.5,
                color='red')
            # korekcijska linija OK
            self.koncKorekcijaOK, = self.axesConcSatni.plot(
                indeks,
                lineOKkorekcija,
                label=glavniOpis+' - korekcija OK',
                linestyle='-',
                linewidth=1.5,
                color='black')
            # korekcijska linija Bad
            self.koncKorekcijaBad, = self.axesConcSatni.plot(
                indeks,
                lineBadkorekcija,
                label=glavniOpis+' - korekcija BAD',
                linestyle='-.',
                linewidth=1.5,
                color='black')
            # postavi y label - mjerna jedinica aktivne komponente
            # postavi y label - mjerna jedinica aktivne komponente
            lab = 'Konc.Satni '+datastore.koncentracija.jedinica
            self.axesConcSatni.set_ylabel(lab)
            # dohvati ostale kanale i plotaj i njih (spremi u pomocne radi on/off opcije)
            ostaliKanali = self.SESSION.get_ostale_kanale(self.AKTIVNI_KANAL)
            for k in ostaliKanali:
                self.crtaj_dodatni_kanal_satni(k)
        except Exception as err:
            logging.error(str(err), exc_info=True)
            #pogreska prilikom crtanja
