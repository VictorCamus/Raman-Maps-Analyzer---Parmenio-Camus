import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import TABLEAU_COLORS
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import scipy.optimize as scopt
import tkinter as tk
from tkinter.ttk import Frame
from pathlib import Path

from classes.peaks import Pic, Fons
from drawing import mapdraw as mapa
from classes.filechannel import InteraccioFigura
from fileio.adapters import open_file
from drawing.plots import plot_peak
from process.basics import find_nearest
from process.statistics import lims_outliers
from FittingProgram import FitSpec
from window.headers import GestorHeaderRAMAN

#Variables inicials
colorsT = list(TABLEAU_COLORS.values())[1:]
font = ("DejaVu Sans", 20)
peakAttr = ["PeakCenter", "FWHM", "Intensity", "Area", "NormInt"]

class AltresMags:
    def __init__(self, pics, magnituds, operacio):
        self.pics = pics # Put the file names of the peak fitting parameters
        self.magnituds = magnituds # Choose one of the following peak magnitudes: ["Peak center", "FWHM", "Intensity", "Normalized Intensity"]
        self.operacio = operacio # Define the operation to do with the magnitudes

#Altres Variables
rangeSpec650a700 = AltresMags(
    [],  # File names of the peak fitting parameters
    [], # Peak magnitudes to combine
    {"Range": [650, 700]}) # Operation to do with the magnitudes

#IMPORTANT: only magnitudes added to this vector will be considered:
VectorExtraMags = {"SpectralRangeInt650-700": rangeSpec650a700}

class SpecType:
    def __init__(self, name, xdata, units, xtitle):
        self.name = name
        self.xdata = xdata
        self.xtitle = xtitle
        
        self.units = units
        
    @property
    def units(self):
        return self._units
    
    @units.setter
    def units(self, value):
        self._units = {"PeakCenter": value,
            "FWHM": value,
            "Area": value,
            "Intensity": 'uA',
            "NormInt": ''}
        
class PintaMapesInterficie:
    def __init__(self):
        self.root = tk.Tk()
        self.root.option_add("*Font", font)
        self.root.winfo_toplevel().title('Mapa interactiu')
        self.root.geometry("2000x1000")

        self.color = {"PeakCenter": "viridis", 
                      "FWHM": "cividis",
                      "Intensity": 'calent',
                      "Area": "inferno",
                      "NormInt": 'calent'}
        
        nomsFmapes = tk.filedialog.askopenfilenames(filetypes = [("AIST", "*.aist"), ("TXT", "*.txt")])
        self.nomsMapes = {Path(nom).stem: Path(nom) for nom in nomsFmapes}

        nomsLlista = list(self.nomsMapes.keys())
        self.file = self.nomsMapes[nomsLlista[0]]
        self.folder = self.file.with_suffix('')
        self.format = self.file.suffix

        self.marcTop = Frame(self.root)
        self.marcTop.grid(row=0, column=0, sticky = 'e')

        self.header = GestorHeaderRAMAN(self, self.marcTop)
        self.label = self.header.view.label
        self.object = self.header.view.object
        self.nommap = self.object['map'].get()
        self.nommag = self.object['mag'].get()
        self.spec_type = self.object['spec_type'].get()
        self.lims = {}

        plt.rcParams["font.size"]=18
        self.fig, self.ax = plt.subplots(nrows=1, ncols=2)

        self.fig.subplots_adjust(left=0.01, right=0.99, bottom=0.15, top=0.9, wspace=0.3)
        # Add an Axes to the right of the main Axes.
        
        self.new_file()
        self.object['map_limInf'].value.set(self.limInf)
        self.object['map_limSup'].value.set(self.limSup)
        
        self.image = self.ax[0].imshow(self.Z, origin="lower", vmin = self.limInf, vmax = self.limSup, extent = [0, self.mida[0], 0, self.mida[1]], interpolation = None)
        self.cax = mapa.create_cbar(self.fig, self.image)
        self.scale = mapa.Escala(self.ax[0])
    
        mapa.ajust_eixos(self.ax[0])
        self.ax[0].set_autoscale_on(True)

        marcMig = tk.Frame(self.root)
        marcMig.grid(row = 3, column = 0, sticky = "nsew")
        marcMig.grid_rowconfigure(0, weight=1)
        marcMig.grid_columnconfigure(0, weight=1)
        self.canvas = FigureCanvasTkAgg(self.fig, master=marcMig)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        
        self.canvas.mpl_connect('button_press_event', lambda event: self.on_click(event, self.ax[0]))
        self.canvas.mpl_connect('motion_notify_event', self.update_mouse)
        self.root.bind('<Configure>', self._trigger_resize)
        self.root.bind_all('<Escape>', lambda event: self.root.quit())
        
        self.zoom = InteraccioFigura(self.ax[0], self.image, self.scale, self.cax, self.mida)

        marcBot = Frame(self.root)
        marcBot.grid(row = 4, column = 0, sticky = 'ew')

        self.object['button1'] = tk.Button(marcBot, text="Dibuixa histograma", command=self.plot_hist)
        self.object['button1'].grid(row = 0, column = 2, pady = 5, padx = 100)

        self.object['button2'] = tk.Button(marcBot, text="Guarda espectre", command=self.save_spec)
        self.object['button2'].grid(row = 0, column = 3, pady = 5, padx = 100)

        self.object['button3'] = tk.Button(marcBot, text="Ajustar espectre", command=lambda: FitSpec(self, self.specs[self.spec_type].xdata, self.I))
        self.object['button3'].grid(row = 0, column = 4, pady = 5, padx = 100)

        self.object['button4'] = tk.Button(marcBot, text="Eixir", command=self.root.quit)
        self.object['button4'].grid(row = 0, column = 5, pady = 5, padx = 100)
        
        self.canvas.draw()
        
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(3, weight=1)  # marcbot

        self.plt_map()
        self.canvas.get_tk_widget().focus_force()
        self.root.mainloop()

    def _trigger_resize(self, event):
        # Cancel·lar el timer del resize ràpid del canal actiu
        if not hasattr(self, 'zoom'): return
        if hasattr(self, "_active_timer_id") and self._active_timer_id:
            self.root.after_cancel(self._active_timer_id)

        # Programar el resize del canal actiu després de 50 ms
        self._active_timer_id = self.root.after(100, self.zoom._resize())
        
    def event_to_pixel(self, event):
        x_pixel = math.floor(self.N[0] / self.mida[0] * event.xdata) + 1
        y_pixel = math.floor(self.N[1] / self.mida[1] * event.ydata) + 1
        return x_pixel, y_pixel
    
    def change_map(self, value):
        self.file = self.nomsMapes[value.widget.get()]
        self.folder = self.file.with_suffix('')
        self.format = self.file.suffix
        self.new_file()
        self.plt_map()

    def new_file(self):
        xdata, self.spectra, self.N, self.mida, self.laser, _ = open_file([self.file], self.format)
        Nx, Ny = self.N

        self.IntInt = np.nansum(self.spectra, axis=1).reshape(Ny, Nx)
        self.Z = self.IntInt.copy()
        self.limInf, self.limSup = lims_outliers(self.Z)
        self.object['laser'].value.set(self.laser)
        
        self.specs = {'nm': SpecType('PL (λ)', xdata['nm'], 'nm', 'λ (nm)'),
                      'eV': SpecType('PL (E)', xdata['eV'], 'eV', 'E (eV)'),
                      '1/cm': SpecType('RAMAN', xdata['1/cm'], 'cm⁻¹', 'q (cm⁻¹)')}
        
        if not Path(self.folder).exists() or next(Path(self.folder).glob("*.txt")) is StopIteration: return

        self.fits = {}
        for file in sorted(Path(self.folder).glob("*.txt")):
            if file.name.endswith("_params.txt"): continue

            header = {}
            with open(file, encoding="utf-8") as f:
                posicio = 0

                for linea in f:
                    if not linea.startswith("#"): break
                    posicio += 1
                    if ":" in linea:
                        clau, valor = linea[1:].split(":", 1)
                        header[clau.strip()] = valor.strip()

            if not header['Nom'] in self.fits: self.fits[header['Nom']] = {}
            dades = np.loadtxt(file, skiprows=2)

            self.rangfit = [float(header['Inici']), float(header['Final'])]
            units = header['Unitats']
            self.fit_start, self.fit_end = sorted(find_nearest(xdata[units], self.rangfit))
            xfit = xdata[units][self.fit_start:self.fit_end]

            if header['Pic'] == 'bkg':
                nvars = dades.shape[1]
                varbls = np.array(dades[:, 2:2+int((nvars-2)/2)].reshape(Ny, Nx))
                bkgclass = Fons(header['Pic'], units, header['Funció'], varbls, xfit = xfit, color = 'tab:blue')
                result = [np.sum(bkgclass.data([i, j])) for i in range(Ny) for j in range(Nx)]
                bkgclass.Intensity = np.array(result).reshape(Ny, Nx)
                self.fits[header['Nom']]['bkg'] = bkgclass
                
                self.object['spec_type'].value.set(units)
                self.spec_type = units
                continue

            centers = dades[:, 2].reshape(Ny, Nx)
            FWHM = dades[:, 3].reshape(Ny, Nx)
            Int = dades[:, 4].reshape(Ny, Nx)
            IntNorm = Int / self.IntInt

            peak = Pic(header['Pic'], units, header["Funció"], centers, FWHM, Int, IntNorm, xfit = xfit, color = colorsT[len(self.fits[header['Nom']])])
            self.fits[header['Nom']][header['Pic']] = peak

        self.object["fits"].configure(values = list(self.fits.keys()))
        self.object["fits"].current(0)
        self.nomfit = list(self.fits.keys())[0]
        
        pics = list(self.fits[self.nomfit].keys())
        pics.remove('bkg')

        self.object["pic1"].configure(values = pics)
        self.object["pic1"].current(0)
        self.pic1 = pics[0]
        
        self.object["pic2"].configure(values = pics)
        self.object["pic2"].current(0)
        self.pic2 = pics[0]

    def update_mouse(self, event):
        if event.inaxes == self.ax[0]:
            x_pixel, y_pixel = self.event_to_pixel(event)

            self.object['track_x'].value.set(x_pixel)
            self.object['track_y'].value.set(y_pixel)
            self.object['track_z'].value.set(float(f"{self.Z[y_pixel-1, x_pixel-1]:.2f}"))

        elif event.inaxes == self.ax[1]:
            puntx = round(event.xdata, 2); punty = round(event.ydata)

            self.object['track_xaxis'].value.set(puntx)
            self.object['track_yaxis'].value.set(punty)

        else:
            for key in ['track_x', 'track_y', 'track_z', 'track_xaxis', 'track_yaxis']: 
                self.object[key].value.set('')
    
    def limit_pixels(self):
        x0 = int(self.zoom.xlims[0] / self.mida[0] * self.N[0])
        x1 = int(self.zoom.xlims[1] / self.mida[0] * self.N[0])
        y0 = int(self.zoom.ylims[0] / self.mida[1] * self.N[1])
        y1 = int(self.zoom.ylims[1] / self.mida[1] * self.N[1])
        return x0, x1, y0, y1
    
    def plt_map(self, event = None, attr = None):
        if attr:
            setattr(self, attr, event.widget.get())
            if attr == 'nommag': self.label['track_z'].config(text = event.widget.get())
        
        self.object['pic1'].configure(state='disabled')
        self.object['pic2'].configure(state='disabled')
        if hasattr(self, 'fits'): 
            pics = list(self.fits[self.nomfit].keys())
            pics.remove('bkg')
        else: 
            for element in ['map', 'fits', 'mag']: self.object[element].configure(state='disabled')
        
        match self.nommap:
            case 'Intensitat':
                self.Z = self.IntInt
                self.object['mag'].configure(values = ["Intensitat"])
                self.object['mag'].set("Intensity")
                self.nommag = "Intensity"
            case 'Pics':
                match self.pic1:
                    case 'bkg' | 'Tots': 
                        self.object['mag'].configure(values = ["Intensity"])
                        self.nommag = 'Intensity'
                    case _: self.object['mag'].configure(values = peakAttr)

                pics.extend(['bkg', 'Tots'])
                self.object['pic1'].configure(values = pics, state='readonly')
                if self.pic1 not in pics: 
                    self.object['pic1'].set(pics[0])
                    self.pic1 = pics[0]
                if self.pic1 == 'Tots': 
                    self.Z = np.zeros_like(self.Z)
                    for key, peak in self.fits[self.nomfit].items():
                        if key == 'bkg': continue

                        self.Z += peak.Intensity

                else: self.Z = getattr(self.fits[self.nomfit][self.pic1], self.nommag).copy()
            case 'P2-P1' | 'P2/P1':
                if self.pic1 not in pics:
                    self.object['pic1'].set(pics[0])
                    self.pic1 = pics[0]

                if self.pic2 not in pics:
                    self.object['pic2'].set(pics[-1])
                    self.pic2 = pics[-1]

                self.object['mag'].configure(values=peakAttr)

                val1 = getattr(self.fits[self.nomfit][self.pic1], self.nommag)
                val2 = getattr(self.fits[self.nomfit][self.pic2], self.nommag)

                self.Z = ops[self.nommap](val2, val1)
                self.Z = val2 - val1 if self.nommap == 'P2-P1' else val2 / val1

                self.object['pic1'].configure(values=pics, state='readonly')
                self.object['pic2'].configure(values=pics, state='readonly')
            case _:
                for magnitud in VectorExtraMags.values():
                    magsCombination = [getattr(self.fits[self.nomfit][pic], mg) for mg, pic in zip(magnitud.magnituds, magnitud.pics)]
                    if type(magnitud.operacio) is dict:
                        xdata = self.specs["nm"].xdata
                        idxInf, idxSup = find_nearest(xdata, magnitud.operacio["Range"])
                        magnitud.Intensity = np.array([np.sum(spec[idxInf:idxSup]) for spec in self.spectra]).reshape(*self.N[::-1])
                        magnitud.magnituds=["Area"]
                    else:
                        magnitud.Intensity = magnitud.operacio(*magsCombination)
                
                mags = np.unique(magnitud.magnituds)
                self.object['mag'].configure(values = mags)
                self.object['mag'].set(mags[0])
                self.nommag = mags[0]
                self.Z = VectorExtraMags[self.nommap].Intensity.copy()

        units = self.specs[self.spec_type].units[self.nommag]
        if self.nommap == 'P2/P1': units = ''
        valors = self.Z[~np.isnan(self.Z)]
        self.limInf, self.limSup = lims_outliers(valors)

        mapa.update_map(self.image, self.color[self.nommag], self.Z, (self.limInf, self.limSup), units, mida = self.mida, cbar = self.cax, interp = 'gaussian')
        self.zoom.midaBase = self.mida
        self.zoom._base_size()
        self.object['map_limInf'].value.set(self.limInf)
        self.object['map_limSup'].value.set(self.limSup)
        self.object['cmap'].value.set(self.color[self.nommag])
        self.ax[0].set_title(f'{self.object["map"].get()} {self.object["pic1"].get() if self.object["map"].get() == "Pic" else ""} {self.object["mag"].get()}')
        self.canvas.draw()
        
        if hasattr(self, 'posx') and hasattr(self, 'posy'): self.plot_spec()

    def on_click(self, event, mapa):
        if event.inaxes != mapa or event.xdata==None or event.ydata==None:
            return
        else:
            self.posx, self.posy = self.event_to_pixel(event)
            self.plot_spec()

    def plot_hist(self):
        def gaussiana(x, x0, sigma, I): #Gaussiana #sigma = FWHM / (2 * np.sqrt(2 * np.log(2)))
            return I * np.exp(-((x - x0) / sigma) ** 2 / 2)
        
        units = self.specs[self.spec_type].units[self.nommag] 
        label = f'{self.nommag} ({units})'
        x0, x1, y0, y1 = self.limit_pixels()
        valors = self.Z[y0:y1, x0:x1].flatten()

        punts = np.linspace(self.limInf, self.limSup, 100)
        HistogramaMapa, limits = np.histogram(valors, bins = 15, range=[self.limInf, self.limSup], density=False)

        centres = (limits[:-1] + limits[1:]) / 2
        pas = 0.9 * (centres[1] - centres[0])
        p_ini = [np.median(valors), np.percentile(valors, 75)-np.percentile(valors, 25), np.max(HistogramaMapa)]
        limits = ([0, 0, 0], [+np.inf, +np.inf, +np.inf])
        
        #Gràfica histograma
        fig2, ax2 = plt.subplots()
        ax2.bar(centres, HistogramaMapa, width=pas, fc='tab:blue',align="center")
        ax2.set(xlabel=label, ylabel='Frequency', title=f'{self.nommap} {self.nommag}')
        fig2.show()
        
        print(f'Ajustant {self.nommap} {self.nommag}')
        try:
            popt, pcov = scopt.curve_fit(gaussiana, centres, HistogramaMapa,\
                p0=p_ini, bounds=limits)
        except RuntimeError:
            print("\n\t\tERROR! L'ajust per mínims quadrats ha fallat.\n")
            return
        
        ax2.plot(punts, gaussiana(punts, *popt), '-', color='tab:red')      
        perr = np.sqrt(np.diag(pcov))

        yint = (ax2.get_ylim()[1]-ax2.get_ylim()[0])
        posx = (ax2.get_xlim()[1]-ax2.get_xlim()[0])*0.6+ax2.get_xlim()[0]
        posy = yint*0.8+ax2.get_ylim()[0]
        ax2.annotate(fr'$x_0$ = {popt[0]:.4g} $\pm$ {perr[0]:.2g} {units if self.nommap != "Ràtio (P2-P1)" else ""}', xy=(posx, posy), xycoords='data')
        ax2.annotate(fr'$\sigma$ = {popt[1]:.3g} $\pm$ {perr[1]:.2g} {units if self.nommap != "Ràtio (P2-P1)" else ""}', xy=(posx, posy-yint*0.1), xycoords='data')    
        ax2.annotate(fr'$I_{{max}}$ = {popt[2]:.3g} $\pm$ {perr[2]:.2g}', xy=(posx, posy-yint*0.2), xycoords='data')
    
    def plot_spec(self):
        self.ax[1].clear()
        self.etiquette = {}
        pos = self.posy - 1, self.posx - 1
        idx = pos[1] + pos[0] * self.N[0]
        self.I = self.spectra[idx,:].copy()
        spec = self.specs[self.spec_type]

        if hasattr(self,'fits'): 
            fit = self.fits[self.nomfit]
            xdata = spec.xdata[self.fit_start:self.fit_end]
            bkg = fit['bkg']

            if self.object['spec_bkg'].value.get(): 
                bkgdata = fit['bkg'].data(pos)
            else: 
                bkgdata = np.zeros_like(bkg.xfit)
                self.I[self.fit_start:self.fit_end] -= fit['bkg'].data(pos)
        else: 
            bkgdata = np.zeros_like(spec.xdata)
            xdata = spec.xdata

        match self.nommap:
            case 'Intensitat': pass
            case 'Pics': 
                match self.pic1:
                    case 'bkg': 
                        self.ax[1].fill_between(xdata, bkgdata, 0, color = 'tab:blue', alpha=0.6)
                    case 'Tots':
                        params = []
                        for key, peak in fit.items():
                            if key == 'bkg': 
                                self.ax[1].fill_between(xdata, bkgdata, 0, color = 'tab:blue', alpha=0.6)
                                continue
                            self.etiquette[key] = plot_peak(xdata, self.ax[1], peak, bkgdata, pos)
                            params.extend([peak.PeakCenter[*pos], peak.FWHM[*pos], peak.Intensity[*pos]])

                        yfit = np.zeros_like(xdata)
                        for key, peak in self.fits[self.nomfit].items(): 
                            if key == 'bkg' and not self.object['spec_bkg'].value.get(): continue
                            yfit += peak.data(pos)

                        self.ax[1].plot(xdata, yfit, 'k-', lw=2, label='Fit total')

                    case _: self.etiquette[self.pic1] = plot_peak(xdata, self.ax[1], fit[self.pic1], bkgdata, pos)

            case 'P2-P1' | 'P2/P1':
                for element in [self.pic1, self.pic2]: self.etiquette[element] = plot_peak(xdata, self.ax[1], fit[element], bkgdata, pos)
            case _:
                for element in VectorExtraMags[self.nommap].pics:
                    self.etiquette[element] = plot_peak(xdata, self.ax[1], fit[element], bkgdata, pos)

        self.dades, = self.ax[1].plot(spec.xdata, self.I, color = 'r', zorder=0)
        self.dades.set_visible(self.object['spec_data'].value.get())

        for element in self.etiquette.values(): element.set_visible(self.object['spec_etiq'].value.get())
        
        self.ax[1].set_title(f"{spec.name} spectrum X={self.posx} Y={self.posy}")
        self.ax[1].set_xlabel(spec.xtitle)
        self.ax[1].set_ylabel(r'Intensity (uA)')
        self.ax[1].tick_params(direction = 'in')

        if not self.lims:
            self.lims['spec_left'], self.lims['spec_right'] = min(xdata), max(xdata)

        self.lims['spec_bot'], self.lims['spec_top'] = 0, 1.15*self.ax[1].get_ylim()[1]
        for key, value in self.lims.items(): self.object[key].value.set(round(value, 2))

        self.ax[1].set_xlim(self.lims['spec_left'], self.lims['spec_right'])
        self.ax[1].set_ylim(self.lims['spec_bot'], self.lims['spec_top'])
        
        self.canvas.draw()
        
    def save_spec(self):
        if not hasattr(self, 'I'): return
        ruta = self.folder / 'Spectra'
        ruta.mkdir(parents = True, exist_ok = True)
        nom = ruta / f'{self.folder.stem}_{self.posx}_{self.posy}'
        np.savetxt(f'{nom}.txt', np.c_[self.specs[self.spec_type].xdata, self.I], delimiter=';', fmt = ['%.4f', '%d'])
        pos = self.posy-1, self.posx-1
        if hasattr(self, 'fits'):
            ruta = f'{self.folder}_{self.posx}_{self.posy} - FIT.txt'
            fit = self.fits[self.nomfit]
            bkg = self.fits[self.nomfit]['bkg']
            peakdata = 0
            for peak in fit.values(): peakdata += peak.data(pos)
            bkgdata = bkg.data(pos)
            data = np.c_[bkg.xfit, peakdata, bkgdata, peakdata-bkgdata]
            with open(f'{nom} - FIT.txt', 'w', encoding='utf-8', newline='') as f:
                f.write(f"#Nom: {[self.nomfit]}\n")
                f.write(f"#Unitats: {[bkg.units]}\n")
                f.write(f"#Pics: {[key for key in fit.keys() if key != 'bkg']}\n")
                f.write(f"#Funcions: {[peak.type for key, peak in fit.items() if key != 'bkg']}\n")
                f.write(f"#Centres: {[str(peak.PeakCenter[*pos]) for key, peak in fit.items() if key != 'bkg']}\n")
                f.write(f"#FWHM: {[str(peak.FWHM[*pos]) for key, peak in fit.items() if key != 'bkg']}\n")
                f.write(f"#Intensitats: {[str(peak.Intensity[*pos]) for key, peak in fit.items() if key != 'bkg']}\n")
                f.write(f'# # # #\n')
                f.write(f"#Fons: {[bkg.type]}\n")
                f.write(f"#Variables: {[str(bkg.varbls[*pos])]}\n\n")
                header = [self.specs[self.spec_type].xtitle, "I (uA)", "bkg", "I-bkg"]
                np.savetxt(f, data, delimiter = '\t', fmt = '%.2f', header = '\t'.join(header))

if __name__ == "__main__":
    PintaMapesInterficie()