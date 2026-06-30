import numpy as np
from pathlib import Path
import pandas as pd
from tkinter import filedialog

filepath = Path(filedialog.askopenfilename(filetypes=[("Arxius AIST", "*.aist")]))
elements = ['AFM','MAG','PHASE','CPD','COND','GRAIN', 'SPV']

folder = filepath.parent # Nom de l'arxiu que s'obri (sense el path)
nom = 1

while True:
    trobat = False

    for tipus in elements:
        
        fitxer_tipus = folder / f'{str(nom)} - {tipus}.xyz'
        if not fitxer_tipus.exists():
            continue
        
        df = pd.read_csv(fitxer_tipus, sep='\t', usecols=[0,1,2], header=None)
        x = df[0].values; y = df[1].values; z = df[2].values
        
        if tipus == 'AFM':
            x = x * 1e-3
            y = y * 1e-3

        if tipus == 'CPD':
            x = x * 1e-3
            y = y * 1e-3

        trobat = True
        base = fitxer_tipus.name
        df_nou = pd.DataFrame({'X': x, 'Y': y, 'Z': z})
        np.savetxt('{}\{}'.format(folder,base),df_nou,fmt='%.5e', delimiter='\t')

    if not trobat:
        break

    nom += 1