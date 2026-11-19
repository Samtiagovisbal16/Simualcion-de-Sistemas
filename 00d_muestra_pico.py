# -*- coding: utf-8 -*-
"""
SIMULACIÓN DE SISTEMAS - CECAR
Paso 0d: MUESTRA DE HORA PICO (ciclo por vehículo, en segundos)

Lee datos/muestra_pico.csv: Vehiculo;Producto;Hora;Espera_s;Flujo_s;Cobro_s;Galones;Notas
  Servicio = Flujo + Cobro      (la columna "Total" de campo incluye la espera: NO es servicio)
  Wq real  = Espera

Como la muestra es pequeña (< 30 por tipo), NO se ajustan distribuciones: se construyen
triangulares por el método de momentos (mínimo y máximo observados y moda tal que la media
de la triangular sea igual a la media observada), que es la opción del curso para pocos datos.

Genera resultados/muestra_pico.json, que usan 05 (modelo) y 04 (validación).
"""
import os
import json
import numpy as np
import pandas as pd
from scipy import stats

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    pass
os.makedirs("resultados", exist_ok=True)

ruta = "datos/muestra_pico.csv"
with open(ruta, encoding="utf-8-sig") as fh:
    enc = fh.readline()
sep = next((d for d in [";", "\t", ","] if d in enc), ",")
df = pd.read_csv(ruta, sep=sep, encoding="utf-8-sig")
df.columns = [c.strip() for c in df.columns]
for c in ["Espera_s", "Flujo_s", "Cobro_s", "Galones"]:
    df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ".").str.replace("~", ""), errors="coerce")
df["tipo"] = df["Vehiculo"].str.lower().map(lambda v: "moto" if "moto" in v else ("camion" if "cami" in v and "camioneta" not in v else "carro"))
df["servicio_s"] = df["Flujo_s"] + df["Cobro_s"]
hh = pd.to_datetime(df["Hora"].astype(str).str.strip(), format="%H:%M", errors="coerce")
df["hora_min"] = hh.dt.hour * 60 + hh.dt.minute

print(f"Vehículos en la muestra: {len(df)} -> " + ", ".join(f"{t}: {n}" for t, n in df['tipo'].value_counts().items()))
if (df["tipo"].value_counts() < 30).any():
    print("¡ATENCIÓN! Menos de 30 datos por tipo: no se ajustan distribuciones; se usan triangulares por momentos.")


def triangular_momentos(x):
    a, b, m = float(np.min(x)), float(np.max(x)), float(np.mean(x))
    moda = min(max(3 * m - a - b, a), b)
    return [round(a, 2), round(moda, 2), round(b, 2)]


print("\n=========== TIEMPOS POR TIPO (segundos) ===========")
print(df.groupby("tipo")[["Espera_s", "Flujo_s", "Cobro_s", "servicio_s"]].agg(["count", "mean", "std", "min", "max"]).round(2).to_string())

moto = df[df["tipo"] == "moto"]
veh = df[df["tipo"] != "moto"]
tri_moto = triangular_momentos(moto["servicio_s"])
tri_cobro = triangular_momentos(veh["Cobro_s"]) if len(veh) >= 2 else [30.0, 50.0, 75.0]
seg_gal = (veh["Flujo_s"] / veh["Galones"]).dropna()

print(f"\nServicio de moto (flujo + cobro): media {moto['servicio_s'].mean():.1f} s -> Triangular{tuple(tri_moto)} s")
print(f"Cobro de carros y camiones (islero ocupado): media {veh['Cobro_s'].mean():.1f} s -> Triangular{tuple(tri_cobro)} s")
if len(seg_gal):
    print(f"Caudal diésel: {seg_gal.mean():.1f} s/galón (de {seg_gal.min():.1f} a {seg_gal.max():.1f}) "
          "-> el flujo de carros y camiones sigue saliendo de los registros del sistema")

wq = df["Espera_s"].to_numpy() / 60
ic = stats.t.interval(0.95, len(wq) - 1, loc=wq.mean(), scale=wq.std(ddof=1) / np.sqrt(len(wq)))
print(f"\nEspera real hasta poner la manguera (incluye pedir el monto y programar el surtidor): media {wq.mean()*60:.1f} s ({wq.mean():.3f} min) | "
      f"IC 95 %: [{ic[0]*60:.0f} ; {ic[1]*60:.0f}] s | n = {len(wq)}")

# ---------------------------------------------------------------------
# Esperas de motos con hora de llegada exacta (ráfaga de hora pico)
# ---------------------------------------------------------------------
extra = {}
if os.path.exists("datos/esperas_motos_pico.csv"):
    e = pd.read_csv("datos/esperas_motos_pico.csv", sep=None, engine="python")
    e.columns = [c.strip() for c in e.columns]
    tt = pd.to_datetime(e["Hora"].astype(str).str.strip(), format="%H:%M:%S")
    t_s = (tt.dt.hour * 3600 + tt.dt.minute * 60 + tt.dt.second).to_numpy().astype(float)
    w_s = pd.to_numeric(e["Espera_s"].astype(str).str.replace(",", "."), errors="coerce").to_numpy()
    d_s = np.diff(np.sort(t_s))
    lam_m = 3600 / d_s.mean()
    pend, _ = np.polyfit(t_s - t_s.min(), w_s, 1)
    r = np.corrcoef(t_s, w_s)[0, 1]
    mu = lam_m / (1 + pend)                     # aproximación de fluido: la espera crece si λ > μ
    ciclo = 3600 / mu
    share_m = 0.814
    if os.path.exists("resultados/resumen_campo.json"):
        share_m = json.load(open("resultados/resumen_campo.json", encoding="utf-8"))["proporcion_tipo"]["moto"]
    lam_total = lam_m / share_m
    prep = max(ciclo - moto["servicio_s"].mean(), 0)
    print("\n=========== RÁFAGA DE MOTOS (hora de llegada con segundos) ===========")
    print(f"Motos: {len(t_s)} en {(t_s.max()-t_s.min())/60:.1f} min | entre llegadas {d_s.mean():.1f} s (CV {d_s.std(ddof=1)/d_s.mean():.2f})")
    print(f"Tasa de llegada de motos ≈ {lam_m:.1f} motos/h  ->  total estimado ≈ {lam_total:.1f} veh/h (motos = {share_m*100:.1f} %)")
    print(f"La espera crece {pend:.3f} s por cada segundo (r = {r:.2f}): la fila se está formando (λ > μ)")
    print(f"Ritmo de atención implícito ≈ {mu:.1f} motos/h -> ciclo por moto ≈ {ciclo:.1f} s (si las atiende un islero)")
    print(f"Servicio medido (flujo + cobro) = {moto['servicio_s'].mean():.1f} s -> PREPARACIÓN (pedir monto, programar surtidor, poner manguera) ≈ {prep:.1f} s")
    print(f"Espera de estas motos: media {w_s.mean():.1f} s (de {w_s.min():.0f} a {w_s.max():.0f} s)")
    wq = np.concatenate([wq, w_s / 60])
    extra = {"lambda_motos_pico": float(lam_m), "lambda_total_pico": float(lam_total),
             "media_entre_llegadas_pico_min": float(60 / lam_total), "ciclo_moto_s": float(ciclo),
             "prep_moto_estimada_s": float(prep), "pendiente_espera": float(pend)}
    print(f"\nEspera real combinada (vehículos cronometrados + ráfaga de motos): media {wq.mean()*60:.1f} s | n = {len(wq)}")

ini = df["hora_min"].min() / 60
fin = (df["hora_min"].max() + 5) / 60
json.dump({"tri_moto_s": tri_moto, "tri_cobro_s": tri_cobro, "ventana_pico": [ini, fin],
           "wq_real_min": [float(v) for v in wq], "n": int(len(df)),
           "seg_por_galon": float(seg_gal.mean()) if len(seg_gal) else None, **extra},
          open("resultados/muestra_pico.json", "w", encoding="utf-8"), indent=2)
pd.DataFrame({"Observacion": range(1, len(wq) + 1), "wq_min": np.round(wq, 4)}).to_csv("datos/wq_real_pico.csv", index=False)
print(f"Ventana de la muestra: {int(ini):02d}:{int(ini%1*60):02d} a {int(fin):02d}:{int(fin%1*60):02d}")
print("Guardado resultados/muestra_pico.json y datos/wq_real_pico.csv")
