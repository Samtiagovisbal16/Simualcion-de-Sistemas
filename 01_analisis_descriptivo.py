# -*- coding: utf-8 -*-
"""
SIMULACIÓN DE SISTEMAS - CECAR
Fase 3 - Paso 1: ANÁLISIS DESCRIPTIVO 
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    pass
CARPETA_DATOS = "datos" if os.path.isdir("datos") else "."
os.makedirs("figuras", exist_ok=True)
AZUL, NARANJA, GRIS = "#0F4C5C", "#E36414", "#6B7B83"

# Lista con las 9 variables a analizar
# Analiza automáticamente todos los archivos que generan 00 y 00b
# (entre_llegadas*, servicio_*), con la columna tiempo_min en MINUTOS
VARIABLES = sorted(f[:-4] for f in os.listdir(CARPETA_DATOS)
                   if f.endswith(".csv") and f.startswith(("entre_llegadas", "servicio_")))
print("Variables a analizar:", VARIABLES)

for VARIABLE in VARIABLES:
    print(f"\n=========================================")
    print(f"   ANALIZANDO VARIABLE: {VARIABLE}")
    print(f"=========================================")
    
    try:
        df = pd.read_csv(f"{CARPETA_DATOS}/{VARIABLE}.csv")
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {VARIABLE}.csv")
        continue
        
    x = df["tiempo_min"].to_numpy()
    n = len(x)
    print("Número de datos:", n)
    if np.ptp(x) == 0:   # EDITADO: variable constante (p. ej. un tiempo fijo anotado igual para todos)
        print(f"Todos los datos valen {x[0]:.4f}: variable CONSTANTE, no tiene dispersión ni forma que analizar.")
        continue
    
    # 3. Medidas de resumen
    q1, mediana, q3 = np.percentile(x, [25, 50, 75])
    resumen = pd.Series({
        "n": n,
        "Media": x.mean(),
        "Mediana": mediana,
        "Desviación estándar": x.std(ddof=1),
        "Coef. de variación (CV)": x.std(ddof=1) / x.mean(),
        "Mínimo": x.min(),
        "Q1 (25 %)": q1,
        "Q3 (75 %)": q3,
        "Máximo": x.max(),
        "Rango": x.max() - x.min(),
        "Asimetría": stats.skew(x, bias=False),
        "Curtosis (exceso)": stats.kurtosis(x, bias=False),
    })
    print(resumen.round(3).to_string())

    # 4. Boxplot
    ric = q3 - q1
    lim_inf = q1 - 1.5 * ric
    lim_sup = q3 + 1.5 * ric
    atipicos = x[(x < lim_inf) | (x > lim_sup)]
    print(f"RIC = {ric:.2f}  |  Límites: [{lim_inf:.2f} ; {lim_sup:.2f}]")
    print("Datos atípicos:", np.sort(atipicos))

    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.boxplot(x, orientation="horizontal", widths=0.5, patch_artist=True,
               boxprops=dict(facecolor="#D6E6EA", color=AZUL, linewidth=1.5),
               medianprops=dict(color=NARANJA, linewidth=2.5),
               whiskerprops=dict(color=AZUL, linewidth=1.5),
               capprops=dict(color=AZUL, linewidth=1.5),
               flierprops=dict(marker="o", markerfacecolor=NARANJA, markeredgecolor=NARANJA, markersize=7))
    for valor, texto in [(q1, "Q1"), (mediana, "Mediana"), (q3, "Q3")]:
        ax.annotate(f"{texto}\n{valor:.2f}", (valor, 1.27), ha="center", fontsize=10, color=AZUL)
    ax.axvline(lim_sup, color=GRIS, ls="--", lw=1)
    ax.annotate(f"Límite superior\nQ3 + 1.5·RIC = {lim_sup:.2f}", (lim_sup - 0.2, 0.62), ha="right", fontsize=9, color=GRIS)
    ax.set_yticks([])
    ax.set_xlabel("Tiempo (min)")
    ax.set_title(f"Diagrama de caja: {VARIABLE}", loc="left", fontsize=12)
    ax.spines[["top", "right", "left"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(f"figuras/01_{VARIABLE}_boxplot.png", dpi=200)
    plt.close()

    # 5. Histograma
    k = int(round(1 + 3.322 * np.log10(n)))
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.hist(x, bins=k, color=AZUL, edgecolor="white", alpha=0.9)
    ax.axvline(x.mean(), color=NARANJA, lw=2, label=f"Media = {x.mean():.2f}")
    ax.axvline(mediana, color=GRIS, lw=2, ls="--", label=f"Mediana = {mediana:.2f}")
    ax.set_xlabel("Tiempo (min)")
    ax.set_ylabel("Frecuencia")
    ax.set_title(f"Histograma: {VARIABLE} (k = {k} clases)", loc="left", fontsize=12)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(f"figuras/01_{VARIABLE}_histograma.png", dpi=200)
    plt.close()

    # 6. Serie
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(np.arange(1, n + 1), x, marker="o", ms=3.5, color=AZUL, lw=1)
    ax.axhline(x.mean(), color=NARANJA, lw=1.5, label="Media")
    ax.set_xlabel("Número de observación (orden de medición)")
    ax.set_ylabel("Tiempo (min)")
    ax.set_title(f"{VARIABLE} en orden de recolección", loc="left", fontsize=12)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(f"figuras/01_{VARIABLE}_serie.png", dpi=200)
    plt.close()

print("\n¡Análisis descriptivo terminado para todas las variables!")


