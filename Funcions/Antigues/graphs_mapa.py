from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import ttk

# Arxiu que gestiona la creació i sincronització de mapes en un notebook de Tkinter.
   
class GestorMapa: # Classe que gestiona la creació i sincronització de mapes en un notebook de Tkinter.
    def __init__(self, app, nom, dades):
        self.app = app
        self.notebook = self.app.notebook
        self.timer_id = None
        self.element = nom
        self._guarda_dades(dades)
        self._crea_pestanya()

    def _guarda_dades(self, dades): # Guarda les dades del mapa en l'aplicació.
        self.app.dades[self.element] = {
            'dades': dades,
        }

    def _crea_pestanya(self): # Crea una pestanya en el notebook per al mapa.
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=self.element)
        self.app.dades[self.element]['frame'] = frame
