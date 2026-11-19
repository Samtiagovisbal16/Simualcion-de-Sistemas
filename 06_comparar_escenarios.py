# -*- coding: utf-8 -*-
"""
SIMULACIÓN DE SISTEMAS - CECAR
Paso 6: EXPERIMENTACIÓN (¿qué pasa con 3 o 4 isleros?)

Cada escenario se corre en FlexSim con el MISMO número de réplicas y se exporta a
  datos/escenario_<nombre>.csv   columnas: Observacion, wq_min, veh_hora,
                                  (opcionales) wq_gasolina, wq_acpm, util_islero_1, ...
El archivo del escenario base debe llamarse escenario_base.csv (o contener 'base').

Para cada medida: media, IC 95 %, diferencia frente al base y prueba t de Welch.
Para Wq: Kruskal-Wallis entre todos los escenarios.
"""
import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    pass
os.makedirs("figuras", exist_ok=True)
os.makedirs("resultados", exist_ok=True)
ALFA = 0.05
COLORES = ["#0F4C5C", "#E36414", "#5B8E7D", "#9A348E", "#B08D57"]


def leer(ruta):
    with open(ruta, encoding="utf-8-sig") as fh:
        enc = fh.readline()
    sep = next((d for d in [";", "\t", ","] if d in enc), ",")
    df = pd.read_csv(ruta, sep=sep, encoding="utf-8-sig")
    df.columns = [c.strip().lower() for c in df.columns]
    for c in df.columns:   # convierte todo a número (acepta coma decimal de Excel en español)
        if not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = pd.to_numeric(df[c].astype(str).str.strip().str.replace(".", "", regex=False)
                                  .str.replace(",", ".", regex=False)
                                  if df[c].astype(str).str.contains(",").any() else df[c].astype(str).str.strip(),
                                  errors="coerce")
    ignorar = [c for c in df.columns if c.startswith(("observ", "scenario", "parameter", "repnum", "rep"))]
    df = df.drop(columns=ignorar, errors="ignore")
    return df.rename(columns={"wqprom": "wq_min", "vehhora": "veh_hora", "wqpico": "wq_pico"})


archivos = sorted(glob.glob("datos/escenario_*.csv"))
if not archivos:
    raise SystemExit("No hay archivos datos/escenario_*.csv")
esc = {os.path.basename(a)[10:-4]: leer(a) for a in archivos}
if not any("base" in k.lower() for k in esc):
    if os.path.exists("datos/validacion_corridas.csv"):
        esc["base"] = leer("datos/validacion_corridas.csv")
        print("No hay escenario_base.csv: se usa datos/validacion_corridas.csv como escenario base (modelo validado)")
    else:
        raise SystemExit("Falta el escenario base: guarde las réplicas del modelo base como datos/escenario_base.csv")
base = next(k for k in esc if "base" in k.lower())

# Utilización media por islero: UtilIsla1 y UtilIsla2 son la carga de cada ISLA (% del tiempo de una persona);
# se divide la carga total entre el número de isleros del escenario.
ISLEROS = {"base": 2, "1islero": 1, "apoyo": 3, "3isleros": 3, "4isleros": 4}
for k, df in esc.items():
    if {"util_islero_1", "util_islero_2"} <= set(df.columns):
        n_isl = next((v for nom, v in ISLEROS.items() if nom in k.lower()), 2)
        df["util_media_islero"] = (df["util_islero_1"] + df["util_islero_2"]) / n_isl
        df.rename(columns={"util_islero_1": "carga_isla_1", "util_islero_2": "carga_isla_2"}, inplace=True)
orden = [base] + [k for k in esc if k != base]
print("Escenarios:", orden, "| base =", base)

medidas = [c for c in esc[base].columns if all(c in esc[k].columns for k in orden)]
filas = []
for m in medidas:
    xb = esc[base][m].dropna()
    for k in orden:
        x = esc[k][m].dropna()
        ic = stats.t.interval(1 - ALFA, len(x) - 1, loc=x.mean(), scale=x.std(ddof=1) / np.sqrt(len(x)))
        if k == base:
            dif = cambio = p = np.nan
        else:
            dif = x.mean() - xb.mean()
            cambio = dif / xb.mean() * 100 if xb.mean() != 0 else np.nan
            p = stats.ttest_ind(x, xb, equal_var=False).pvalue
        filas.append([m, k, len(x), x.mean(), ic[0], ic[1], dif, cambio, p,
                      "" if k == base else ("Diferente" if p < ALFA else "Sin diferencia")])
tabla = pd.DataFrame(filas, columns=["Medida", "Escenario", "n", "Media", "IC inf", "IC sup",
                                     "Dif. vs base", "Cambio %", "p (Welch)", "Decisión"])
pd.set_option("display.width", 200)
print(tabla.round(4).to_string(index=False))
tabla.to_csv("resultados/comparacion_escenarios.csv", index=False)
print("Guardado resultados/comparacion_escenarios.csv")

col_wq = next((c for c in medidas if c in ("wq_pico",)), None) or \
    next((c for c in medidas if c.startswith("wq") and "gas" not in c and "acpm" not in c), None)
if col_wq and len(orden) > 2:
    p_kw = stats.kruskal(*[esc[k][col_wq].dropna() for k in orden]).pvalue
    print(f"\nKruskal-Wallis sobre {col_wq} entre todos los escenarios: p = {p_kw:.4f}")

if col_wq:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    medias = [esc[k][col_wq].mean() for k in orden]
    err = [stats.t.ppf(0.975, esc[k][col_wq].count() - 1) * esc[k][col_wq].std(ddof=1) / np.sqrt(esc[k][col_wq].count())
           for k in orden]
    ax.bar(orden, medias, yerr=err, capsize=8, color=COLORES[:len(orden)], alpha=0.85)
    for i, mval in enumerate(medias):
        ax.annotate(f"{mval:.3f}", (i, mval), ha="center", va="bottom", xytext=(0, 6), textcoords="offset points")
    ax.set_ylabel(f"{col_wq} (min)"); ax.set_title(f"{col_wq} por escenario (IC 95 %)", loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout(); plt.savefig("figuras/06_escenarios_wq.png", dpi=200); plt.show()