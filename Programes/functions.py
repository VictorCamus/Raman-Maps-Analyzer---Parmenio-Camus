from pathlib import Path
import numpy as np
import sys

sys.path.insert(1, r'C:\Users\vcamu\Documents\UV\funcions-python\Programes-Parmenio\Funcions')

from process.basics import truncar_significatives

def lector_txts():
    nomstxt = sorted(Path().glob("*.txt"))
    noms = [nom.stem for nom in nomstxt]
    return noms

def lims_quartils(arr):
    quart1 = np.percentile(arr, 10)
    quart3 = np.percentile(arr, 90)
    iqr = quart3 - quart1
    inf = quart1 - 4 * iqr; sup = quart3 + 4 * iqr
    lim_inf = max(inf, np.min(arr))
    lim_sup = min(sup, np.max(arr))
    lim_inf = truncar_significatives(lim_inf, 2, cap_a = 'avall')
    lim_sup = truncar_significatives(lim_sup, 2, cap_a = 'amunt')
    return lim_inf, lim_sup

def plot_peak(xdata, ax, peak, bkg, pos):
    color = peak.color; name = peak.name
    ydata = peak.data(pos)
    idx = trobar(peak.xfit, peak.PeakCenter[*pos])
    # ax.plot(xdata, ydata, color = color)
    ax.fill_between(xdata, ydata+bkg, bkg, color=color, alpha=0.6)
    peakcenter = np.interp(peak.PeakCenter[*pos], peak.xfit, xdata)
    etiquette = ax.annotate(f'{name} ({peakcenter:.2f})', xy=(peakcenter, peak.Intensity[*pos]+bkg[idx]),
    xytext=(0, 10), textcoords='offset points', ha='center', color = 'k', fontweight = 'bold', family = 'Arial')
    
    return etiquette

def trobar(arr, value):
    arr = np.array(arr)
    idx = np.argmin((np.abs(arr-value)))
    return idx

def lorentz(x: float, x0: float, FWHM: float, A: float) -> float:
    return A /  (1 + ((x - x0) / (FWHM / 2)) ** 2)
    
def gaussian(x: float, x0: float, FWHM: float, A: float) -> float:
    sigma = FWHM / (2 * np.sqrt(2 * np.log(2)))
    return A * np.exp(-((x - x0) / sigma) ** 2 / 2)

def bkg_constant(x: float, y0: float):
    return np.full_like(x, y0)

Peaks = {'G': gaussian, 'L': lorentz}
Bkgs = {'C': bkg_constant}

def fitspectrum(pics, bkg):

    def model(x, *params):
        y = np.zeros_like(x, dtype=float)

        n_peaks = len(pics)

        for i, tipus in enumerate(pics):
            x0   = params[3*i]
            fwhm = params[3*i + 1]
            I    = params[3*i + 2]

            y += Peaks[tipus](x, x0, fwhm, I)

        bkg_params = params[3*n_peaks:]
        y += Bkgs[bkg](x, *bkg_params)

        return y

    return model


class Ajust:
    def __init__(self, nom, PeakNames, PeakFuncs, bkg, units, rang = None, p_init = None, limits = None, threshold = 0):
        self.nom = nom # Name of the fit
        self.PeakNames = PeakNames # Name of the peaks in the fit
        self.PeakFuncs = PeakFuncs
        self.bkg = bkg
        self.units = units
        self.rang = rang # Spectral range to fit 
        self.p_init = p_init # Seed parameters for the fit.
        self.limits = limits # Limits for the fit parameters
        self.numPics = len(PeakNames)
        self.threshold = threshold
        
        self.funcio = fitspectrum(PeakFuncs, bkg) # Function to fit
        self.peaks = {}
        self.PeakFunctions = {name: Peaks[func] for name, func in zip(PeakNames, PeakFuncs)}
    
    @property
    def Intensity(self):
        Intensity = 0
        for peak in self.peaks.values():
            Intensity += peak.Intensity
        return Intensity

    @property
    def NormInt(self):
        NormInt = 0
        for peak in self.peaks.values():
            NormInt += peak.NormInt
        return NormInt
        
class Pic:
    def __init__(self, name, units, func, PeakCenter, FWHM, Intensity, NormInt, xfit = None, color = 'green'):
        self.name = name
        self.units = units
        self.type = func
        self.func = Peaks[func]
        self.PeakCenter = PeakCenter
        self.FWHM = FWHM
        self.Intensity = Intensity
        self.NormInt = NormInt
        self.xfit = xfit
        self.color = color

        self.Area = self.Intensity*self.FWHM/(2*np.sqrt(np.log(10)))*np.sqrt(np.pi)
        
        self.labels = {"PeakCenter": r"Peak center (cm$^{-1}$)",
                       "FWHM": r"FWHM (cm$^{-1}$)",
                       "Area": r"Intensity (a.u.)",
                       "Intensity": r"Intensity (a.u.)",
                       "NormInt": r"Normalized Intensity (a.u.)"}
        
    def data(self, pos, xdata = None):
        if not xdata: xdata = self.xfit
        params = [self.PeakCenter[*pos], self.FWHM[*pos],self.Intensity[*pos]] 
        return self.func(xdata, *params)

class Fons:
    def __init__(self, name, units, func, varbls, xfit = None, color = 'tab:blue'):
        self.name = name
        self.units = units
        self.type = func
        self.func = Bkgs[func]
        self.varbls = varbls
        self.xfit = xfit
        self.color = color

    def data(self, pos, xdata = None):
        if not xdata: xdata = self.xfit
        return self.func(xdata, *np.atleast_1d(self.varbls[*pos]))
