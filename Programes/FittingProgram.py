import numpy as np
from scipy.interpolate import CubicSpline
from pybaselines import Baseline
from scipy.optimize import curve_fit
from scipy.signal import find_peaks, peak_widths
from math import floor, ceil  
from tkinter import filedialog
from pathlib import Path
from functions import trobar, Ajust
import sys
from dataclasses import dataclass

sys.path.insert(1, r'C:\Users\vcamu\Documents\UV\funcions-python\Programes-Parmenio\Funcions')

from fileio.adapters import open_file

def spike_removal(y, width_threshold=3, prominence_threshold = 1000, moving_average_window=10, width_param_rel=0.8):                    
    # Detects and replaces spikes in the input spectrum signal with interpolated values.
    # Based on the publication by N. Coca-Lopez "An intuitive approach for spike removal in Raman spectra 
    # based on peaks’ prominence and width" https://doi.org/10.1016/j.aca.2024.342312
    canviat = False
    peaks, _ = find_peaks(y, prominence=prominence_threshold, width=[0, width_threshold])
    spikes = np.zeros(len(y), dtype=bool)
    widths, _, widths_left_end, widths_right_end = peak_widths(y, peaks, rel_height=width_param_rel)
    for width, ext_a, ext_b in zip(widths, widths_left_end, widths_right_end):
        spikes[floor(ext_a):ceil(ext_b)] = True
    y_out = y.copy()
    moving_average_window=moving_average_window
    for i, spike in enumerate(spikes):
        if spike:
            window = np.arange(max(i - moving_average_window, 0), min(i + moving_average_window + 1, len(y)))
            window_exclude_spikes = window[spikes[window] == False]
            spline_interp = CubicSpline(window_exclude_spikes, y[window_exclude_spikes])
            y_out[i] = spline_interp(i)
            canviat = True
    return y_out, canviat

def ajust_pic(x, y, fit, p_init):
    #Buscador de pics
    IdxInf = trobar(x, fit.rang[0])
    IdxSup = trobar(x, fit.rang[1])
    
    popt = np.full(len(p_init), np.nan)
    perr = np.full(len(p_init), np.nan)
    trobat = False
    x = x[IdxInf:IdxSup]
    y = y[IdxInf:IdxSup]

    if np.sum (y) > fit.threshold:
        #Ajust no lineal
        try:
            popt, pcov = curve_fit(fit.funcio, x, y, p0=p_init, bounds=fit.limits, maxfev = 300)
            perr = np.sqrt(np.diag(pcov))
            trobat = True
        except ValueError:
            print("\n\t\tERROR! Les dades introduïdes a l'ajust no són vàlides. \n")
        except RuntimeError:
            print("\n\t\tERROR! L'ajust per mínims quadrats ha fallat. \n")
    else: trobat = True

    return popt, perr, trobat

@dataclass
class Info:
    nom: str
    pic: str
    func: str
    units: str
    inici: float
    final: float
        
def write_peak(ruta, info, data, length):
    with open(f'{ruta}.txt', 'w', encoding='utf-8', newline='') as f:
        f.write(f"#Nom: {info.nom}\n")
        f.write(f"#Pic: {info.pic}\n")
        f.write(f"#Funció: {info.func}\n")
        f.write(f"#Unitats: {info.units}\n")
        f.write(f'#Inici: {info.inici}\n')
        f.write(f'#Final: {info.final}\n\n')
        header = ["x", "y"] + [f"p{i}" for i in range(length)] + [f"err_p{i}" for i in range(length)]
        np.savetxt(f, data, delimiter = '\t', fmt = '%.3f', header = '\t'.join(header))

def write_bkg(ruta, info, data):
    with open(f'{ruta}.txt', 'w', encoding='utf-8', newline='') as f:
        f.write(f"#Nom: {info.nom}\n")
        f.write(f"#Funció: {info.func}\n")
        f.write(f"#Unitats: {info.units}\n")
        f.write(f'#Inici: {info.inici}\n')
        f.write(f'#Final: {info.final}\n\n')
        header = ["x", "y"] + ["Background intensity"]
        np.savetxt(f, data, delimiter = '\t', fmt = '%.3f', header = '\t'.join(header))
        
def FuncioAjust(file, fits, fonsSplineGlobal=False):
    resultatsAjustos = {fit.nom: {peak: [] for peak in [*fits[fit.nom].PeakNames, 'bkg']} for fit in fits.values()}

    print(f'Obrint {file.stem}')
    xdata, ydata, _, dims, _, units = open_file([file], file.suffix)
    N = dims[0]*dims[1]
    if fonsSplineGlobal:
        baseline_fitter = Baseline(x_data=xdata[units])
        bkgMatrix = []
        for intensity in ydata:
            bkg, params = baseline_fitter.mixture_model(intensity)
            x = i % dims[0] + 1; y = i // dims[0] + 1
            bkgMatrix.append([x, y, *bkg])    
    for fit in fits.values():
        xdataUnits = xdata[fit.units]
        print(f'Fit {fit.nom}:\n')
        p_init = fit.p_init
        for i, intensity in enumerate(ydata):   
            if i%100 == 0:
                print(f"Ajustant espectre {i+1}/{N}...\n")
            if fonsSplineGlobal:
                intensity -= bkgMatrix[i][2:]
            y_out, canviat = spike_removal(intensity)
            if canviat: intensity = y_out
            
            x = i % dims[0] + 1; y = i // dims[0] + 1
            
            popt, perr, trobat = ajust_pic(xdataUnits, intensity, fit, p_init)
            if not trobat:
                print(f"Espectre {i+1}/{N}:\n")
                print(f"X: {x}, Y: {y}\n")
            for idx, peak in enumerate(fit.PeakNames):
                ifit = 3*idx
                liniaResultats=[x, y, *popt[ifit:ifit+3], *perr[ifit:ifit+3]]
                resultatsAjustos[fit.nom][peak].append(liniaResultats)
                
            
            val = len(fit.PeakNames)
            liniaFons = [x, y, *popt[3*val:], *perr[3*val:]]
            resultatsAjustos[fit.nom]['bkg'].append(liniaFons)
            
    lenFons = len(popt[3*val:])
    #Gravació de resultats a fitxers
    print("Guardant resultats...")
    for key, fit in fits.items():
        ruta = file.with_suffix('') / f'{fit.nom}'
        ruta.parent.mkdir(parents=True, exist_ok=True)
        for peak, func in zip(fit.PeakNames, fit.PeakFuncs):
            info = Info(key, peak, func, fit.units, fit.rang[0], fit.rang[1])
            write_peak(f'{ruta}_{peak}', info, resultatsAjustos[key][peak], 3)

        info = Info(key, 'bkg', fit.bkg, fit.units, fit.rang[0], fit.rang[1])   
        write_peak(f'{ruta}_bkg', info, resultatsAjustos[key]['bkg'], lenFons)
    if fonsSplineGlobal:
        ruta = file.with_suffix('') / "SplineGlobal"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        info = Info(file.stem, _, 'Splinebkg', units, xdata[units][0], xdata[units][-1])   
        write_bkg(f'{ruta}_bkg', info, bkgMatrix)

    print("Finalitzat correctament")

if __name__ == '__main__':
    # Seed parameters for the fit.
    parametersFit1 = [
        621, 3, 400, # P1: x0, FWHM, A
        630, 7, 2000, # P2: x0, FWHM, A
        641, 4, 400, # P3: x0, FWHM, A
        250] # Baseline
        
    # Limits for the fit parameters.
    limitsFit1 = (
    #Lower limits 
        [615, 1, 50, # P1 Intensity
        625, 3, 200, # P2 Intensity
        635, 1, 50, # P3 Intensity
        0], # Baseline
    #Upper limits
        [625, 200, +np.inf, # P1 Intensity
        635, 200, +np.inf, # P2 Intensity
        645, 200, +np.inf, # P3 Intensity
        500]) # Baseline

    fit1 = Ajust(
        nom = "3peaksGO2ndOrder", # Name of the fit
        PeakNames = ["2D", "D+D'", "2D'"], # Name of the peaks in the fit
        PeakFuncs = ['G', 'G', 'G'], # Functions for single peak representation
        bkg = 'C',
        units = 'nm', # Units: nm, eV, 1/cm
        rang = [618, 650], # Spectral range to fit 
        p_init = parametersFit1, # Seed parameters
        limits = limitsFit1,
        threshold = 10000) # Limits for the fit parameters

    parametersFit2 = [
        690, 56, 26000, # P1: x0, FWHM, A
        750, 68, 10000, # P2: x0, FWHM, A
        100] # Baseline
        
    # Limits for the fit parameters.
    limitsFit2 = (
    #Lower limits 
        [670, 15, 500, # P1: x0, FWHM, A
        720, 20, 2000, # P2: x0, FWHM, A
        0], # Baseline
    #Upper limits
        [700, 150, +np.inf, # P1: x0, FWHM, A
        780, 200, +np.inf, # P2: x0, FWHM, A
        500]) # Baseline

    fit2 = Ajust(
        nom = "PL2peaksTPP", # Name of the fit
        PeakNames = ["Q'(0,0)", "Q'(0,1)"], # Name of the peaks in the fit
        PeakFuncs = ['L', 'G'], # Functions for single peak representation
        bkg = 'C',
        units = 'nm', # Units: nm, eV, 1/cm
        rang = [655, 810], # Spectral range to fit 
        p_init = parametersFit2, # Seed parameters
        limits = limitsFit2,
        threshold = 1000) # Limits for the fit parameters

    #IMPORTANT: only fits added to this vector will be done:
    fits = {'3peaksGO2ndOrder': fit1, 'PL2peaksTPP': fit2}
    nomsFmapes = filedialog.askopenfilenames(filetypes = [("TXT", "*.txt"), ("AIST", "*.aist")])
    for nom in nomsFmapes: 
        file = Path(nom)
        FuncioAjust(file, fits, fonsSplineGlobal=False)
