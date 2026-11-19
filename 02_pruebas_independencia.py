# -*- coding: utf-8 -*-
"""
SIMULACIÓN DE SISTEMAS - CECAR
Fase 3 - Paso 2: PRUEBAS DE INDEPENDENCIA (AUTOMATIZADO)
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.stats.diagnostic import acorr_ljungbox

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    pass
CARPETA_DATOS = "datos" if os.path.isdir("datos") else "."
os.makedirs("figuras", exist_ok=True)
AZUL, NARANJA, GRIS = "#0F4C5C", "#E36414", "#6B7B83"
ALFA = 0.05


# Analiza automáticamente todos los archivos que generan 00 y 00b
# (entre_llegadas*, servicio_*), con la columna tiempo_min en MINUTOS
VARIABLES = sorted(f[:-4] for f in os.listdir(CARPETA_DATOS)
                   if f.endswith(".csv") and f.startswith(("entre_llegadas", "servicio_")))
print("Variables a analizar:", VARIABLES)

for VARIABLE in VARIABLES:
    print(f"\n=========================================")
    print(f"   PRUEBAS DE INDEPENDENCIA: {VARIABLE}")
    print(f"=========================================")
    try:
        x = pd.read_csv(f"{CARPETA_DATOS}/{VARIABLE}.csv")["tiempo_min"].to_numpy()
    except FileNotFoundError:
        print(f"Error: No se encontró {VARIABLE}.csv")
        continue
    n = len(x)
    if np.ptp(x) == 0:   # EDITADO: variable constante
        print(f"Todos los datos valen {x[0]:.4f}: variable CONSTANTE, las pruebas de independencia no aplican.")
        continue
    
    # (a) Gráfico de dispersión
    rng = np.random.default_rng(1)
    dep = np.zeros(n); dep[0] = x.mean()
    for i in range(1, n):
        dep[i] = 0.85 * dep[i - 1] + 0.15 * x.mean() + rng.normal(0, 1.2)

    fig, axs = plt.subplots(1, 2, figsize=(10, 4.4))
    for ax, serie, titulo, color in [(axs[0], x, f"Nuestros datos ({VARIABLE})", AZUL),
                                     (axs[1], dep, "Ejemplo de datos DEPENDIENTES", NARANJA)]:
        r = np.corrcoef(serie[:-1], serie[1:])[0, 1]
        ax.scatter(serie[:-1], serie[1:], s=22, color=color, alpha=0.8)
        ax.set_title(f"{titulo}\nr = {r:.3f}", loc="left", fontsize=11)
        ax.set_xlabel("$x_i$"); ax.set_ylabel("$x_{i+1}$")
        ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(f"figuras/02_{VARIABLE}_dispersion.png", dpi=200)
    plt.close()
    
    # (b) Autocorrelograma
    banda = 1.96 / np.sqrt(n)
    fig, ax = plt.subplots(figsize=(9, 3.8))
    retardos = min(20, n // 2 - 1)   # EDITADO: con pocos datos (camiones) no se pueden pedir 20 retardos
    plot_acf(x, lags=retardos, alpha=ALFA, ax=ax, title="", color=AZUL, vlines_kwargs={"colors": AZUL})
    ax.axhline(banda, color=NARANJA, ls="--", lw=1); ax.axhline(-banda, color=NARANJA, ls="--", lw=1)
    ax.set_title(f"Autocorrelograma (retardos 1 a {retardos})", loc="left", fontsize=12)
    ax.set_xlabel("Retardo k"); ax.set_ylabel("$r_k$")
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(f"figuras/02_{VARIABLE}_autocorrelograma.png", dpi=200)
    plt.close()
    
    # (c-1) Rachas sobre/bajo la mediana
    mediana = np.median(x)
    signos = np.where(x > mediana, "+", "-")[x != mediana]
    n1, n2 = np.sum(signos == "+"), np.sum(signos == "-")
    rachas = 1 + np.sum(signos[1:] != signos[:-1])
    media_R = 2 * n1 * n2 / (n1 + n2) + 1
    var_R = 2 * n1 * n2 * (2 * n1 * n2 - n1 - n2) / ((n1 + n2) ** 2 * (n1 + n2 - 1))
    z_med = (rachas - media_R) / np.sqrt(var_R)
    p_med = 2 * (1 - stats.norm.cdf(abs(z_med)))
    
    # (c-2) Rachas ascendentes/descendentes
    d = np.sign(np.diff(x)); d = d[d != 0]
    rachas_ad = 1 + np.sum(d[1:] != d[:-1])
    media_ad = (2 * n - 1) / 3
    var_ad = (16 * n - 29) / 90
    z_ad = (rachas_ad - media_ad) / np.sqrt(var_ad)
    p_ad = 2 * (1 - stats.norm.cdf(abs(z_ad)))
    
    # (c-3) Ljung-Box
    lb = acorr_ljungbox(x, lags=[min(10, n // 2 - 1)], return_df=True)   # EDITADO
    q_lb, p_lb = lb["lb_stat"].iloc[0], lb["lb_pvalue"].iloc[0]
    
    tabla = pd.DataFrame({
        "Prueba": ["Rachas mediana", "Rachas asc/desc", f"Ljung-Box ({min(10, n // 2 - 1)})"],
        "Estadístico": [f"Z = {z_med:.3f}", f"Z = {z_ad:.3f}", f"Q = {q_lb:.3f}"],
        "Valor p": [p_med, p_ad, p_lb],
    })
    tabla["Decisión (α = 0.05)"] = np.where(tabla["Valor p"] >= ALFA, "No se rechaza H0", "Se rechaza H0")
    print(tabla.round(4).to_string(index=False))
    
    if (tabla["Valor p"] >= ALFA).all():
        print("=> CONCLUSIÓN: los datos SON independientes.")
    else:
        print("=> CONCLUSIÓN: hay evidencia de dependencia.")
    # EDITADO: con 3 pruebas a la vez, la probabilidad de al menos un rechazo falso es ~14 %.
    # Criterio complementario de Bonferroni (α/3) para decidir en casos límite.
    if not (tabla["Valor p"] >= ALFA).all():
        if (tabla["Valor p"] >= ALFA / 3).all():
            print(f"   Con corrección de Bonferroni (α/3 = {ALFA/3:.4f}) NO se rechaza la independencia (caso límite).")
        else:
            print(f"   Aun con corrección de Bonferroni (α/3 = {ALFA/3:.4f}) se rechaza la independencia.")

print("\n¡Pruebas de independencia terminadas!")

