import numpy as np
import os
import pandas as pd

import tkinter as tk
from tkinter import filedialog, ttk, messagebox, StringVar, DoubleVar, BooleanVar
from etiquetes import tab, Default, add_colorcombobox, add_combobox, add_entry, add_scale, add_label, complete_grid
from gestor_menu import FuncionsCompartides

# Arxiu que gestiona el menú principal de l'aplicació.
# Conté les classes per a gestionar les accions del menú, les condicions
# i les funcions compartides entre diferents gestors.

class GestorMenu: # Classe que gestiona el menú principal de l'aplicació.
    def __init__(self, app):
        self.app = app
        self._configurar_menu()

    def _configurar_menu(self): # Crea el menú principal de l'aplicació.
        app = self.app

        app.gestor_arxiu = GestorArxiu(app)
        app.gestor_eixos = GestorGrafica(app)
        app.gestor_dades = GestorDades(app)
        app.root.config(menu=app.menu)

class Condicions: # Mixin per a comprovar condicions abans d'executar accions.
    def pestanyes_comprova(self): # Comprova si hi ha pestanyes obertes al notebook.
        if not self.app.notebook.tabs():
            messagebox.showinfo("Informació", "No hi ha cap fitxer obert.")
            return False
        return True

    def condicions_guardar(self): # Comprova si es compleixen les condicions per a guardar un fitxer.
        return self.pestanyes_comprova()

        
class GestorBase(Condicions, FuncionsCompartides):  # Classe base per a gestionar les accions comunes de l'aplicació.
    def __init__(self, app):
        self.app = app

class GestorArxiu(GestorBase):  # Classe que gestiona les accions del menú "Arxiu" de l'aplicació.
    def __init__(self, app):
        super().__init__(app)  # Inicialitza la classe base
        
        accions = [
            ("Obrir fitxer", self._obrir_fitxer, '<Control-o>'),
            ("Guardar imatge informació", self._guardar_fitxer, '<Control-g>'),
            ("Tancar fitxer", self._tancar_fitxer, '<Control-t>'),
            ("SEPARATOR"),
            ("Eixir", self.app.root.quit),
        ]
        
        self.afegir_menu("Arxiu", accions)  # Crida a la funció comuna d'afegir menú
        
    def _obrir_fitxer(self):
        filepath = filedialog.askopenfilename(filetypes=[("Arxius de text", "*.txt")])
        if not filepath: return

        self.app.carpeta = filepath.replace('.txt','')
        self.app.label_inici.place_forget()
        nom = os.path.basename(self.app.carpeta)
        dades = pd.read_csv(filepath,sep=' ', header=None)

        # Finestra de selecció
        win = tk.Toplevel(self.app.root)
        win.title("Configura la gràfica")

        # Mostra les dades en vertical
        frame_dades = ttk.Frame(win)
        frame_dades.pack(side="left", fill="y", padx=10, pady=10)
        ttk.Label(frame_dades, text="Dades:").pack()
        listbox = tk.Listbox(frame_dades, width=40, height=20)
        # Convertim cada columna a string, amb notació científica si és numèrica
        dades_fmt = dades.copy()
        for col in dades_fmt.columns:
            if dades_fmt[col].dtype.kind in "fci":  # float, complex o int
                dades_fmt[col] = dades_fmt[col].apply(lambda x: f"{x:.{4}e}" if x == x else "")
            else: dades_fmt[col] = dades_fmt[col].astype(str)

        for fila in dades_fmt.values:
            fila_format = "  ".join(str(val).rjust(2) for i, val in enumerate(fila))
            listbox.insert("end", fila_format)

        listbox.pack()

        # Opcions de gràfic
        frame_opts = ttk.Frame(win)
        frame_opts.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        ttk.Label(frame_opts, text="Tipus de gràfic:").pack()
        tipus_var = tk.StringVar(value="plot")
        ttk.Radiobutton(frame_opts, text="Plot bàsic", variable=tipus_var, value="plot").pack(anchor="w")
        ttk.Radiobutton(frame_opts, text="Plot amb error", variable=tipus_var, value="errorbar").pack(anchor="w")
        ttk.Radiobutton(frame_opts, text="Histograma de barres", variable=tipus_var, value="bar").pack(anchor="w")

        def dibuixa():
            if not hasattr(self.app, 'dataConfig'): setattr(self.app, 'dataConfig', [])
            if not hasattr(self.app, 'data'): setattr(self.app, 'data', {})
            
             # Dades seleccionades
            xdata = np.array(dades[0]).ravel()
            ydata = np.array(dades[1]).ravel()
            
            try: zdata = np.array(dades[2]).ravel()
            except: zdata = None
                
            if tipus_var.get() == "plot":
                line, = self.app.ax.plot(xdata, ydata, '.', markersize=1.0, color='blue', linewidth=1.0, label = nom)
                format = "line"
            elif tipus_var.get() == "errorbar":
                line = self.app.ax.errorbar(xdata, ydata, zdata, fmt='o', color='blue', capsize=5, label = nom)
                format = "errorbar"
            elif tipus_var.get() == "bar":
                line = self.app.ax.bar(xdata, ydata, color='blue', align = 'edge', edgecolor='blue', label = nom)
                format = "bar"

            self.app.dataConfig.append((nom, line, format))
            self.app.data[nom] = {'x': xdata, 'y': ydata, 'z': zdata}
            
            self.app.fig.canvas.draw_idle()
            win.destroy()

        ttk.Button(frame_opts, text="Dibuixa", command=dibuixa).pack(pady=10)
        
    def _guardar_fitxer(self): # Guarda les dades de les pestanyes obertes en un fitxer.
        if not self.condicions_guardar(): return

    def _tancar_fitxer(self): # Tanca el fitxer actual i neteja les dades associades.
        self.app.notebook.forget(self.app.notebook.select())
        # Torna a mostrar el missatge inicial
        self.app.label_inici.place(relx=0.5, rely=0.5, anchor='center')
        self.app.data = {}

class GestorDades(GestorBase):  # Classe que gestiona les accions del menú "Dades" de l'aplicació.
    def __init__(self, app):
        super().__init__(app)  # Inicialitza la classe base

        accions = [
            ("Gestionar dades", self._data),
            ("Afegir llegenda", self._add_legend)
        ]
        
        self.afegir_menu("Dades", accions)  # Crida a la funció comuna d'afegir menú
        
    def _data(self):
        
        if not hasattr(self.app,'dataConfig'):
            messagebox.showerror('Gestionar dades', f'No hi ha encara dades disponibles')
            return
         
        def _grid_for_element(nom, obj, format):
            if format == "line":
                return [
                    (("_name", StringVar), ("Nom:", add_entry), (obj.set_label, {}), {"set_value": obj.get_label()}),
                    (("_linestyle", StringVar), ("Línia:", add_combobox), (obj.set_linestyle, {}), {"set_value": obj.get_linestyle(), "options": Default.line_style()}),
                    (("_markerstyle", StringVar), ("Punts:", add_combobox), (obj.set_marker, {}), {"set_value": obj.get_marker(), "options": Default.marker_style()}),
                    (("_color", StringVar), ("Color:", add_colorcombobox), (obj.set_color, {}), {"set_value": obj.get_color(), "colors": Default.colors()}),
                    (("_markersize", DoubleVar), ("Mida marcador:", add_entry), (obj.set_markersize, {}), {"set_value": obj.get_markersize()}),
                    (("_linewidth", DoubleVar), ("Gruix línia:", add_entry), (obj.set_linewidth, {}), {"set_value": obj.get_linewidth()}),
                    (("_alpha", DoubleVar), ("Transparència:", add_scale), (obj.set_alpha, {}), {"set_value": obj.get_alpha() or 1}),
                ]
            elif format == "errorbar":
                line = obj.lines[0]
                caps = obj.lines[1]
                errbars = obj.lines[2]
                first_cap = caps[0] if caps else None
                first_errbar = errbars[0] if errbars else None
                
                grid = [
                    (("_name", StringVar), ("Nom:", add_entry), (obj.set_label, {}), {"set_value": obj.get_label()}),
                    (("_linestyle", StringVar), ("Línia:", add_combobox), (line.set_linestyle, {}), {"set_value": line.get_linestyle(), "options": Default.line_style()}),
                    (("_markerstyle", StringVar), ("Punts:", add_combobox), (line.set_marker, {}), {"set_value": line.get_marker(), "options": Default.marker_style()}),
                    (("_color", StringVar), ("Color:", add_colorcombobox), (line.set_color, {}), {"set_value": line.get_color(), "colors": Default.colors()}),
                    (("_markersize", DoubleVar), ("Mida marcador:", add_entry), (line.set_markersize, {}), {"set_value": line.get_markersize()}),
                    (("_linewidth", DoubleVar), ("Gruix línia:", add_entry), (line.set_linewidth, {}), {"set_value": line.get_linewidth()}),
                    (("_alpha", DoubleVar), ("Transparència:", add_scale), (line.set_alpha, {}), {"set_value": line.get_alpha() or 1.0, "from_":0.0, "to":1.0, "resolution":0.01}),
                    (("_zorder", DoubleVar), ("Z-order:", add_entry), (line.set_zorder, {}), {"set_value": line.get_zorder() or 0}),
                    (("_errorcolor", StringVar), ("Color barres d'error:", add_colorcombobox), (lambda c: [eb.set_color(c) for eb in errbars], {}), {"set_value": first_errbar.get_color() if errbars else line.get_color(), "colors": Default.colors()}),
                    (("_errorwidth", DoubleVar), ("Gruix barres d'error:", add_entry), (lambda w: [eb.set_linewidth(w) for eb in errbars], {}), {"set_value": first_errbar.get_linewidth()[0] if errbars else line.get_linewidth()}),
                    (("_capcolor", StringVar), ("Color capçals:", add_colorcombobox), (lambda c: [eb.set_color(c) for eb in caps], {}), {"set_value": first_cap.get_color() if errbars else line.get_color(), "colors": Default.colors()}),
                ]

                return grid
            elif format == "bar":
                bars = obj  # llista de Rectangle
                first = bars[0]

                return [
                    (("_label", StringVar), ("Nom:", add_entry), (obj.set_label, {}), {"set_value": obj.get_label() or ""}),
                    (("_facecolor", StringVar), ("Color interior:", add_colorcombobox), (lambda c: [p.set_facecolor(c) for p in bars], {}), {"set_value": first.get_facecolor(), "colors": Default.colors()}),
                    (("_width", DoubleVar), ("Amplària:", add_entry), (lambda w: [b.set_width(w) for b in bars], {}), {"set_value": first.get_width()}),
                    (("_edgecolor", StringVar), ("Color vora:", add_colorcombobox), (lambda c: [p.set_edgecolor(c) for p in bars], {}), {"set_value": first.get_edgecolor(), "colors": Default.colors()}),
                    (("_linewidth", DoubleVar), ("Gruix vora:", add_entry), (lambda w: [p.set_linewidth(w) for p in bars], {}), {"set_value": first.get_linewidth()}),
                    (("_alpha", DoubleVar), ("Transparència:", add_scale), (lambda a: [p.set_alpha(a) for p in bars], {}), {"set_value": first.get_alpha() or 1.0, "from_":0.0, "to":1.0, "resolution":0.01}),
                    (("_zorder", DoubleVar), ("Z-order:", add_entry), (lambda z: [p.set_zorder(z) for p in bars], {}), {"set_value": first.get_zorder() or 0}),
                ]
            else:
                return []
        
        self.create_window("Configurar dades", gridBuilder = _grid_for_element, tabConfig = self.app.dataConfig, figure = self.app.fig)
    
    def _add_legend(self):
        yesorno = {"Sí": True, "No": False}
        
        def _grid_size():
            return [
                (("_visible", BooleanVar), ("Mostrar:", add_combobox), (self._toggle_legend, {}), {"set_value": "No", "options": yesorno}),
                (("width", DoubleVar), ("Mida:", add_entry), (self._set_legend_width, {}), {}),
                (("textsize", DoubleVar), ("Posició:", add_entry), (self._set_legend_textsize, {}), {})
            ]
        
        self.create_window("Ajustar mida", gridBuilder=_grid_size, figure=self.app.fig)

    def _toggle_legend(self, value, key):
        """Funció per mostrar o amagar la llegenda."""
        legend = self.app.ax.get_legend()
        if legend: legend.set_visible(value)
        else: self.app.ax.legend()  # Si no hi ha llegenda, la creem
        
        self.app.fig.canvas.draw_idle()  # Actualitzar el gràfic

    def _set_legend_width(self, width, key):
        """Funció per ajustar l'amplada de la llegenda."""
        legend = self.app.ax.get_legend()
        if legend:
            legend.set_bbox_to_anchor((1, 1), transform=self.app.ax.transAxes)  # Ajustar la posició
            legend.set_frame_on(True)  # Assegurar que el marc estigui activat
            legend.set_title("Llegenda")  # Opcional: afegir un títol a la llegenda
            # Aquí podries ajustar l'amplada si és necessari
        self.app.fig.canvas.draw_idle()  # Actualitzar el gràfic

    def _set_legend_textsize(self, textsize, key):
        """Funció per ajustar la mida del text de la llegenda."""
        legend = self.app.ax.get_legend()
        if legend:
            for text in legend.get_texts():
                text.set_fontsize(textsize)
        self.app.fig.canvas.draw_idle()  # Actualitzar el gràfic
                
class GestorGrafica(GestorBase):  # Classe que gestiona les accions del menú "Arxiu" de l'aplicació.
    def __init__(self, app):
        super().__init__(app)  # Inicialitza la classe base

        accions = [
            ("Mida", self._axes_size),
            ("Títols", self._axes_titles),
            ("Límits", self._axes_lims),
            ("Ticks", self._axes_ticks)
        ]
        
        self.afegir_menu("Eixos", accions)  # Crida a la funció comuna d'afegir menú

    def _axes_size(self):

        tabConfig = [("Figura", self.app.frame_canvas, (self.app.frame_canvas.winfo_width(), self.app.frame_canvas.winfo_height()))]
        
        def _grid_size(nom, obj, getter):
            return [
                (("width", DoubleVar),  ("Eix X:", add_entry), (obj.place_configure, {}), {"set_value": getter[0]}),
                (("height", DoubleVar), ("Eix Y:", add_entry), (obj.place_configure, {}), {"set_value": getter[1]})
            ]
        
        self.create_window("Ajustar mida", gridBuilder = _grid_size, tabConfig = tabConfig, figure = self.app.fig)
        
    def _axes_titles(self):
        
        def _set_labelpad(value, text_obj=None, nom=None):
            if nom == "Títol":
                x, y = text_obj.get_position()
                text_obj.set_position((x, value / 400 + 1.0))  # ajustem amb punts a relatiu
            else: text_obj.labelpad = value

        def _get_labelpad(text_obj, nom):
            if nom == "Títol":
                return (text_obj.get_position()[1] - 1.0) * 400  # ajustem amb punts a relatiu
            else:
                return text_obj.labelpad
            
        if not hasattr(self.app.ax, "custom_title"):
            self.app.ax.custom_title = self.app.ax.text(
                0.5, 1.05, self.app.ax.get_title(),
                ha='center', va='bottom',
                transform=self.app.ax.transAxes
            )

        tabConfig = [
            ("Títol", (self.app.ax.custom_title, self.app.ax.custom_title)),
            ("Eix X", (self.app.ax.xaxis.label, self.app.ax.xaxis)),
            ("Eix Y", (self.app.ax.yaxis.label, self.app.ax.yaxis))
        ]

        def _grid_titles(nom, obj):
            return [
                (("_label", StringVar), ("Nom:", add_entry), (obj[0].set_text, {}), {"set_value": obj[0].get_text()}),
                (("_font", StringVar), ("Tipografia:", add_combobox), (obj[0].set_fontfamily, {}), {"set_value": obj[0].get_fontname(), "options": Default.fonts()}),
                (("_fontsize", DoubleVar), ("Mida:", add_entry), (obj[0].set_fontsize, {}), {"set_value": obj[0].get_fontsize()}),
                (("_color", StringVar), ("Color:", add_colorcombobox), (obj[0].set_color, {}), {"set_value": obj[0].get_color(), "colors": Default.colors()}),
                (("_fontweight", StringVar), ("Format:", add_combobox), (obj[0].set_fontweight, {}), {"set_value": obj[0].get_fontweight(), "options": Default.format()}),
                (("_style", StringVar), ("Estil:", add_combobox), (obj[0].set_style, {}), {"set_value": obj[0].get_style(), "options": Default.text_style()}),
                (("_pad", DoubleVar), ("Separació:", add_entry), (_set_labelpad, {'text_obj': obj[1], 'nom': nom}), {"set_value": _get_labelpad(obj[1], nom)}),
            ]

        self.create_window("Editar eixos (Títols)", gridBuilder = _grid_titles, tabConfig = tabConfig, figure = self.app.fig)

    def _axes_lims(self):

        tabConfig = [
            ("Eix X", (self.app.ax.get_xlim(), self.app.ax.get_xscale()), (self.app.ax.set_xlim, self.app.ax.set_xscale), "left", "right"),
            ("Eix Y", (self.app.ax.get_ylim(), self.app.ax.get_yscale()), (self.app.ax.set_ylim, self.app.ax.set_yscale), "bottom", "top"),
        ]

        def _grid_lims(nom, getter, setter, lim_inf, lim_sup):
            return [
                # Estructura: ((var_name, var_type), (label, object), setter, {getter, **extra})
                ((lim_inf, DoubleVar), ("Límit inferior:", add_entry), (setter[0], {}), {"set_value": getter[0][0]}),
                ((lim_sup, DoubleVar), ("Límit superior:", add_entry), (setter[0], {}), {"set_value": getter[0][1]}),
                (("_scale", StringVar), ("Escala:", add_combobox), (setter[1], {}),{"set_value": getter[1], "options": Default.scale()})
            ]
                
        self.create_window("Editar eixos (Límits)", gridBuilder = _grid_lims, tabConfig = tabConfig, figure = self.app.fig)

    def _axes_ticks(self):

        def _set_ticks(axis, vars, tick_inf = None, tick_sup = None, tick_step = None):
            from math import floor
            from contextlib import contextmanager

            if tick_inf is not None: vars["tick_inf"].set(tick_inf)
            if tick_sup is not None: vars["tick_sup"].set(tick_sup)
            if tick_step is not None: vars["tick_step"].set(tick_step)
            
            tick_inf = vars["tick_inf"].get(); tick_sup = vars["tick_sup"].get(); tick_step = vars["tick_step"].get()
            
            n_steps = int(floor((tick_sup - tick_inf) / tick_step)) + 1
            ticks = [tick_inf + i * tick_step for i in range(n_steps)]

            @contextmanager
            def autoscale_turned_off(ax=None):
                lims = [ax.get_xlim(), ax.get_ylim()]
                yield
                ax.set_xlim(*lims[0])
                ax.set_ylim(*lims[1])
            
            with autoscale_turned_off(ax = self.app.ax):
                axis(ticks)

        def _set_property(value, axis, prop):
            for tick in axis.get_majorticklabels(): getattr(tick, f"set_{prop}")(value)

        def _get_property(axis, prop):
            return getattr(axis.get_majorticklabels()[0], f"get_{prop}")()
        
        def _set_pad(value, axis):
            for tick in axis.get_major_ticks(): tick.set_pad(value)

        def _get_pad(axis):
            return axis.get_major_ticks()[0].get_pad()

        tabConfig = [
            ("Eix X", (self.app.ax.set_xticks, self.app.ax.xaxis), (self.app.ax.get_xticks(), self.app.ax.xaxis)),
            ("Eix Y", (self.app.ax.set_yticks, self.app.ax.yaxis), (self.app.ax.get_yticks(), self.app.ax.yaxis)),
        ]
        
        def _grid_ticks(nom, setter, getter):
            return [
                (("tick_inf", DoubleVar), ("Tick inferior:", add_entry), (_set_ticks, {"axis": setter[0], "vars": True}), {"set_value": getter[0][0]}),
                (("tick_sup", DoubleVar), ("Tick superior:", add_entry), (_set_ticks, {"axis": setter[0], "vars": True}), {"set_value": getter[0][-1]}),
                (("tick_step",  DoubleVar), ("Interval:", add_entry), (_set_ticks, {"axis": setter[0], "vars": True}), {"set_value": getter[0][1]-getter[0][0]}),
                (("_fontname", StringVar), ("Tipografia:", add_combobox), (_set_property, {"axis": setter[1], "prop": "fontname"}), {"set_value": _get_property(getter[1], "fontname"), "options": Default.fonts()}),
                (("_fontsize", DoubleVar), ("Mida:", add_entry), (_set_property, {"axis": setter[1], "prop": "fontsize"}), {"set_value": _get_property(getter[1], "fontsize")}),
                (("_color", StringVar), ("Color:", add_colorcombobox), (_set_property, {"axis": setter[1], "prop": "color"}), {"set_value": _get_property(getter[1], "color"), "colors": Default.colors()}),
                (("_fontweight", StringVar), ("Format:", add_combobox), (_set_property, {"axis": setter[1], "prop": "fontweight"}), {"set_value": _get_property(getter[1], "fontweight"), "options": Default.format()}),
                (("_style", StringVar), ("Estil:", add_combobox), (_set_property, {"axis": setter[1], "prop": "style"}), {"set_value": _get_property(getter[1], "style"), "options": Default.text_style()}),
                (("_pad", DoubleVar), ("Separació", add_entry), (_set_pad, {'axis': setter[1]}), {"set_value": _get_pad(getter[1])}),
                (("_rotation", DoubleVar), ("Rotació:", add_entry), (_set_property, {"axis": setter[1], "prop": "rotation"}), {"set_value": _get_property(getter[1], "rotation")}),
            ]

        self.create_window("Editar eixos (Ticks)", gridBuilder = _grid_ticks, tabConfig = tabConfig, figure = self.app.fig)