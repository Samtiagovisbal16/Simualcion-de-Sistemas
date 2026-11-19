# -*- coding: utf-8 -*-
"""
SIMULACIÓN DE SISTEMAS - CECAR
Paso 0b: ¿QUÉ FRANJAS HORARIAS USAR PARA LAS LLEGADAS?

Responde con estadística (no a ojo) qué horas pueden modelarse con una misma
distribución de tiempo entre llegadas:
  1. Calcula la tasa de llegada λ de cada hora.
  2. Une horas CONSECUTIVAS cuyos tiempos entre llegadas no difieren
     (Kolmogorov-Smirnov de dos muestras y Mann-Whitney, α = 0.05).
  3. Compara contra las franjas de campo y contra los turnos de trabajo.
  4. Escribe datos/entre_llegadas_F<k>_<hh>a<hh>.csv (uno por franja) para
     ajustarlos con 01, 02 y 03, y resultados/franjas.json para el script 05.
"""
import os
import json
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import config

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    pass
os.makedirs("figuras", exist_ok=True)
os.makedirs("resultados", exist_ok=True)
AZUL, NARANJA, GRIS = "#0F4C5C", "#E36414", "#6B7B83"
ALFA = 0.05
MIN_DATOS_HORA = 10       # una hora con menos datos se une a la franja vecina sin probar
MODO = "estadistico"      # "estadistico" | "campo" (columna Franja_Horaria) | "turnos"
TURNOS = [(5, 21)]   # día 05-21 (2 isleros) y noche 21-05 (1 islero); 29 = 05 del día siguiente

df = pd.read_csv("datos/datos_limpios.csv")
h0, h1 = config.VENTANA
x = df.dropna(subset=["entre_llegadas"])
x = x[(x["hora"] >= h0) & (x["hora"] < h1)]
print(f"Se analizan las horas de la ventana {h0:02d}:00-{h1:02d}:00 (config.py)")

# ---------------------------------------------------------------------
# 1. Tasa por hora
# ---------------------------------------------------------------------
tabla = x.groupby("hora")["entre_llegadas"].agg(n="count", media="mean", desv="std")
tabla["lambda_veh_h"] = 60 / tabla["media"]
tabla["CV"] = tabla["desv"] / tabla["media"]
print("Tasa de llegada por hora observada:")
print(tabla.round(3).to_string())

# ---------------------------------------------------------------------
# 2. Agrupación estadística de horas consecutivas
# ---------------------------------------------------------------------
horas = list(tabla.index)
grupos = [[horas[0]]]
decisiones = []
for h in horas[1:]:
    actual = x.loc[x["hora"].isin(grupos[-1]), "entre_llegadas"]
    nueva = x.loc[x["hora"] == h, "entre_llegadas"]
    consecutiva = h == grupos[-1][-1] + 1
    if not consecutiva:
        grupos.append([h])
        decisiones.append((h, "nueva franja (hora no consecutiva)", np.nan, np.nan))
        continue
    if len(nueva) < MIN_DATOS_HORA:
        grupos[-1].append(h)
        decisiones.append((h, f"se une (solo {len(nueva)} datos)", np.nan, np.nan))
        continue
    p_ks = stats.ks_2samp(actual, nueva).pvalue
    p_mw = stats.mannwhitneyu(actual, nueva, alternative="two-sided").pvalue
    if p_ks >= ALFA and p_mw >= ALFA:
        grupos[-1].append(h)
        decisiones.append((h, "se une (no hay diferencia)", p_ks, p_mw))
    else:
        grupos.append([h])
        decisiones.append((h, "NUEVA franja (llegadas diferentes)", p_ks, p_mw))

print("\nDecisión hora por hora (comparada con la franja que se venía armando):")
print(pd.DataFrame(decisiones, columns=["hora", "decisión", "p K-S", "p Mann-Whitney"]).round(4).to_string(index=False))

# Franjas con pocos datos: se unen a la vecina con la tasa más parecida
def n_de(g):
    return int(x["hora"].isin(g).sum())

def lam_de(g):
    return 60 / x.loc[x["hora"].isin(g), "entre_llegadas"].mean()

while len(grupos) > 1 and min(n_de(g) for g in grupos) < config.MIN_DATOS_FRANJA:
    i = min(range(len(grupos)), key=lambda k: n_de(grupos[k]))
    vecinos = [j for j in (i - 1, i + 1) if 0 <= j < len(grupos) and
               (grupos[j][-1] + 1 == grupos[i][0] or grupos[i][-1] + 1 == grupos[j][0])]
    if not vecinos:
        break
    j = min(vecinos, key=lambda k: abs(lam_de(grupos[k]) - lam_de(grupos[i])))
    print(f"Franja {min(grupos[i]):02d}-{max(grupos[i])+1:02d} tiene {n_de(grupos[i])} datos (< {config.MIN_DATOS_FRANJA}): "
          f"se une con {min(grupos[j]):02d}-{max(grupos[j])+1:02d}")
    a, b = sorted([i, j])
    grupos[a] = sorted(grupos[a] + grupos[b])
    del grupos[b]


def resumen_grupos(lista, nombre):
    filas = []
    for g in lista:
        datos = x.loc[x["hora"].isin(g), "entre_llegadas"]
        filas.append([f"{min(g):02d}:00-{(max(g) + 1) % 24:02d}:00", len(datos), 60 / datos.mean(),
                      datos.std() / datos.mean()])
    r = pd.DataFrame(filas, columns=["franja", "n", "λ (veh/h)", "CV"])
    muestras = [x.loc[x["hora"].isin(g), "entre_llegadas"] for g in lista if len(g)]
    p_kw = stats.kruskal(*muestras).pvalue if len(muestras) > 1 else np.nan
    print(f"\n--- Franjas {nombre} ---")
    print(r.round(3).to_string(index=False))
    if len(muestras) > 1:
        print(f"Kruskal-Wallis entre franjas: p = {p_kw:.4f} -> "
              + ("las franjas SÍ son diferentes entre sí" if p_kw < ALFA else "las franjas NO difieren entre sí"))
    return r


resumen_grupos(grupos, "propuestas por la prueba estadística")

if "franja_campo" in df.columns:
    campo = [sorted(x.loc[x["franja_campo"] == f, "hora"].unique().tolist())
             for f in x["franja_campo"].dropna().unique()]
    campo = sorted([c for c in campo if c], key=lambda c: c[0])
    resumen_grupos(campo, "de campo (columna Franja_Horaria)")
else:
    campo = None

turnos = [[h for h in horas if a <= h < b or a <= h + 24 < b] for a, b in TURNOS]
turnos = [t for t in turnos if t]
resumen_grupos(turnos, "por turno de trabajo")

# ---------------------------------------------------------------------
# 3. Elegir y guardar
# ---------------------------------------------------------------------
elegidas = {"estadistico": grupos, "campo": campo or grupos, "turnos": turnos}[MODO]
for f in glob.glob("datos/entre_llegadas_F*.csv"):
    os.remove(f)
franjas = []
print(f"\nFranjas elegidas (MODO = '{MODO}') y archivos generados:")
for k, g in enumerate(elegidas, 1):
    h_ini, h_fin = min(g), max(g) + 1
    var = f"entre_llegadas_F{k}_{h_ini:02d}a{h_fin % 24:02d}"
    datos = x.loc[x["hora"].isin(g), "entre_llegadas"].to_numpy()
    pd.DataFrame({"tiempo_min": np.round(datos, 4)}).to_csv(f"datos/{var}.csv", index=False)
    franjas.append({"variable": var, "h_ini": int(h_ini), "h_fin": int(h_fin), "n": int(len(datos)),
                    "lambda_veh_h": float(60 / datos.mean())})
    aviso = "  <- menos de 30 datos: amplíe la franja o use MODO='turnos'" if len(datos) < 30 else ""
    print(f"  datos/{var}.csv  ({len(datos)} datos, λ = {60/datos.mean():.1f} veh/h){aviso}")
json.dump(franjas, open("resultados/franjas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("Guardado resultados/franjas.json")

# ---------------------------------------------------------------------
# 4. Figura para el artículo
# ---------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9.5, 4))
ax.bar(tabla.index, tabla["lambda_veh_h"], color=AZUL, alpha=0.85, width=0.8, label="λ por hora")
for k, f in enumerate(franjas):
    ax.hlines(f["lambda_veh_h"], f["h_ini"] - 0.4, f["h_fin"] - 0.6, color=NARANJA, lw=3,
              label="λ de la franja" if k == 0 else None)
    ax.axvspan(f["h_ini"] - 0.5, f["h_fin"] - 0.5, color=GRIS if k % 2 else "white", alpha=0.12)
ax.set_xlabel("Hora del día"); ax.set_ylabel("Llegadas (veh/h)")
ax.set_xticks(tabla.index)
ax.set_title("Tasa de llegada por hora y franjas homogéneas", loc="left")
ax.legend(frameon=False); ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout(); plt.savefig("figuras/00b_franjas_horarias.png", dpi=200); plt.close()
print("Figura: figuras/00b_franjas_horarias.png")
