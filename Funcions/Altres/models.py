import sys
from dataclasses import dataclass
import numpy as np
from pandas import read_csv

sys.path.insert(1, r'C:\Users\Parmenio\OneDrive - Universitat de Valencia\Escritorio\Doctorat\Programetes\Funcions')
sys.path.insert(1, r'C:\Users\ASUS\OneDrive - Universitat de València\Escritorio\Doctorat\Programetes\Funcions')

# @dataclass
# class SPV_model_aproximat:
#     name: list = [r'$\eta$', r'$\tau$', r'$y_0$', r'$y_{max}$','B']
#     init_values: list = [-1, 1, self.SPV[0], self.SPV[-1], 0]
#     units: list = ['', 'min', 'mV', 'mV','mV']
#     mins: list = [-5, 0, inf, inf, inf]
#     maxs: list = [0, +inf, +inf, +inf, +inf]
#     varies: list = [True, True, False, True, False]

class Models:
    registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Models.registry[cls.__name__] = cls

class SPV(Models):
    def __init__(self, file = None, x = np.array([None]), y = np.array([None])): # x: Temps (min). y: SPV (mV)
        self.x, self.y = x, y
        self.ax_labels = ('Time (min)', 'SPV (mV)')
        
        self.recal = 0
        
        if file:
            if 'Apagat' in file.name:
                ences = file.name.replace('Apagat','Encés')
                fitxences = file.parent.parent/'Encés'/ences
                SPVences = read_csv(fitxences,sep=' ',usecols=[1], header=None)
                SPVences = np.array(SPVences).ravel()
                self.y = self.y + SPVences[-1]
                self.posicio = 0.6
            if 'Encés' in file.name:
                self.posicio = 0.9
                
        self.params = {  # Nom del paràmetre: (var_name, init_value, vary, min, max)
            'p0': ('p0', -1, True, -10, 0),
            'p1': ('p1', 1, True, 0, np.inf),
            'p2': ('p2', self.y[0], False, -np.inf, np.inf),
            'p3': ('p3', self.y[-1], True, -np.inf, np.inf),
            'p4': ('p4', 0, False, -np.inf, np.inf)
        }

        self.vars = {
            'p0': ('η', ''),        
            'p1': ('τ', 'min'),     
            'p2': ('SPV₀', 'mV'),   
            'p3': ('SPVmax', 'mV'), 
            'p4': ('A', 'mV')       
        }

    @staticmethod
    def func(x, p0, p1, p2, p3, p4):
        kT = 25.6
        x = np.asarray(x)
        
        # Evitar valors zero o massa petits per p0 i p1
        p0_safe = p0 if abs(p0) > 1e-12 else np.sign(p0)*1e-12
        p1_safe = p1 if abs(p1) > 1e-12 else 1e-12

        try:
            expo1 = np.exp(-(p2 - p3)/(2 * p0_safe * kT))
            expo2 = np.exp(-x / (p1_safe )) # Es pot afegiru np.exp(-p3 / (p0_safe * kT) multiplicant a p1_safe.
            sinhf = np.sinh(-(p2 - p3)/(2 * p0_safe * kT))
            y = p3 - p0_safe * kT * np.log(1 + 2 * expo1 * sinhf * expo2) + p4
            # Substituir NaNs o Infs per valors raonables
            y = np.nan_to_num(y, nan=0.0, posinf=1e10, neginf=-1e10)
        except Exception:
            # Si hi ha algun error, retornar zeros amb la mateixa mida
            y = np.zeros_like(x)
        return y

class SPVdiff(Models):
    def __init__(self, file = None, x = np.array([None]), y = np.array([None])):
        self.x, self.y = x, y
        self.ax_labels = ('Time (min)', r'$SPV_{diff}$ (mV)')
        self.recal = 0
        self.params = { # Nom del paràmetre: (var_name, init_value, vary, min, max)
            'p0': ('p0', -1, True, -10, 0),
            'p1': ('p1', 1, True, 0, np.inf),
            'p3': ('p3', self.y.max(), True, -np.inf, np.inf),
            'p4': ('p4', 0, False, -np.inf, np.inf)
        }
        
        self.vars = {
            'p0': ('η', ''),        
            'p1': ('τ', 'min'),       
            'p3': ('SPVmax', 'mV'), 
            'p4': ('A', 'mV')       
        }
        
    @staticmethod
    def func(x, p0, p1, p3, p4):
        """
        Funció diff segura per a lmfit.
        També garanteix la mateixa mida de x i evita NaNs/Infs.
        """
        kT = 25.6
        x = np.asarray(x)
        
        p0_safe = p0 if abs(p0) > 1e-12 else np.sign(p0)*1e-12
        p1_safe = p1 if abs(p1) > 1e-12 else 1e-12

        try:
            terme = p3 / (p0_safe * kT)
            expo1 = np.exp(terme/2)
            sinhf = np.sinh(terme/2)
            invexpo1 = np.exp(-terme/2)
            invsinhf = np.sinh(-terme/2)
            y = -p0_safe*kT*np.log((1 + 2*expo1*sinhf*np.exp(-x/(p1_safe*np.exp(-terme)))) *
                                    (1 + 2*invexpo1*invsinhf*np.exp(-x/p1_safe))) + p4
            y = np.nan_to_num(y, nan=0.0, posinf=1e10, neginf=-1e10)
        except Exception:
            y = np.zeros_like(x)
        return y

# @dataclass
# class Parameter:
#     name: str = None
#     var_name: str = None
#     unit: str = None
#     init_value: float = 0.0
#     min: float = -float('inf')
#     max: float = float('inf')
#     vary: bool = True