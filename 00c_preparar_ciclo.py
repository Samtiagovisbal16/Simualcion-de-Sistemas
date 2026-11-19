# -*- coding: utf-8 -*-
"""
SIMULACIÓN DE SISTEMAS - CECAR
Paso 0c: DATOS DEL CICLO COMPLETO (muestra en hora pico)

Lee datos/datos_ciclo.csv con 5 marcas de tiempo por vehículo (HH:MM:SS):
  T1 = llega a la fila (frena)              T2 = el islero empieza a atenderlo
  T3 = empieza a marcar galones             T4 = deja de marcar
  T5 = el vehículo arranca y se va (ya pagó)
y calcula:
  Wq real            = T2 - T1   (espera)
  Servicio total     = T5 - T2   (lo que ocupa al islero)
  Flujo              = T4 - T3   (lo que medía el sistema)
  Atención sin flujo = Servicio total - Flujo (saludo, tanque, cobro, cambio, salida)

Archivos que genera en datos/:
  servicio_total_<tipo>.csv  -> servicio completo por tipo (si hay suficientes datos)
  servicio_noflujo.csv       -> atención sin flujo, todos los tipos juntos
  wq_real_pico.csv           -> espera real de cada vehículo (para validar)
  entre_llegadas_pico.csv    -> solo para comparar con los datos anteriores
y resultados/resumen_ciclo.json (lo usan 05 y 04).
"""
import os
import json
import numpy as np
import pandas as pd
from scipy import stats
import config

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    pass
os.makedirs("datos", exist_ok=True)
os.makedirs("resultados", exist_ok=True)

ARCHIVO = "datos/datos_ciclo.csv"
MIN_DATOS = getattr(config, "MIN_DATOS_SERVICIO", 30)

with open(ARCHIVO, encoding="utf-8-sig") as fh:
    enc = fh.readline()
sep = next((d for d in [";", "\t", ","] if d in enc), ",")
df = pd.read_csv(ARCHIVO, sep=sep, encoding="utf-8-sig", dtype=str)
df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
print("Columnas:", list(df.columns), "| filas:", len(df))
for c in ["T1", "T2", "T3", "T4", "T5", "Vehiculo"]:
    if c not in df.columns:
        raise SystemExit(f"Falta la columna {c}. Use el formato de formato_toma_datos.csv")


def seg_del_dia(serie):
    s = serie.astype(str).str.strip().str.lower()
    s = s.str.replace(r"a\.?\s*m\.?", " AM", regex=True).str.replace(r"p\.?\s*m\.?", " PM", regex=True)
    s = s.str.replace(r"\s+", " ", regex=True).str.strip()
    res = pd.Series(np.nan, index=s.index)
    for fmt in ["%H:%M:%S", "%I:%M:%S %p", "%H:%M", "%I:%M %p"]:
        t = pd.to_datetime(s, format=fmt, errors="coerce")
        res = res.fillna(t.dt.hour * 3600 + t.dt.minute * 60 + t.dt.second)
    return res


for c in ["T1", "T2", "T3", "T4", "T5"]:
    df[c + "_s"] = seg_del_dia(df[c])
if (df[[c + "_s" for c in ["T1", "T2", "T3", "T4", "T5"]]] % 60 == 0).all().all():
    print("¡ATENCIÓN! Ninguna marca tiene segundos. Para esta muestra los segundos son indispensables.")


def tipo(v):
    v = str(v).lower()
    if "moto" in v or "frasco" in v:
        return "moto"
    if ("cami" in v and "camioneta" not in v) or "bus" in v or "volqueta" in v:
        return "camion"
    return "carro"


df["tipo"] = df["Vehiculo"].map(tipo)
df["fecha"] = df["Fecha"].astype(str).str.strip() if "Fecha" in df.columns else "1"
df["wq"] = (df["T2_s"] - df["T1_s"]) / 60
df["s_total"] = (df["T5_s"] - df["T2_s"]) / 60
df["flujo"] = (df["T4_s"] - df["T3_s"]) / 60
df["noflujo"] = df["s_total"] - df["flujo"]

orden_ok = (df["T1_s"] <= df["T2_s"]) & (df["T2_s"] <= df["T3_s"]) & (df["T3_s"] < df["T4_s"]) & (df["T4_s"] <= df["T5_s"])
malas = df[~orden_ok | df[["wq", "s_total", "flujo"]].isna().any(axis=1)]
if len(malas):
    print(f"\n¡ATENCIÓN! {len(malas)} filas con marcas vacías o en desorden (se excluyen):")
    print(malas[["Vehiculo", "T1", "T2", "T3", "T4", "T5"]].to_string())
    df = df.drop(malas.index)


def guardar(nombre, valores, col="tiempo_min"):
    v = np.round(np.asarray(valores, dtype=float), 4)
    pd.DataFrame({col: v}).to_csv(f"datos/{nombre}.csv", index=False)
    aviso = "" if len(v) >= MIN_DATOS else f"  <- menos de {MIN_DATOS} datos"
    print(f"  datos/{nombre}.csv ({len(v)} datos){aviso}")


print("\nArchivos generados:")
fuente = {}
for t in ["moto", "carro", "camion"]:
    sub = df[df["tipo"] == t]
    if len(sub) >= MIN_DATOS:
        guardar(f"servicio_total_{t}", sub["s_total"])
        fuente[t] = "total"
    else:
        if os.path.exists(f"datos/servicio_total_{t}.csv"):
            os.remove(f"datos/servicio_total_{t}.csv")
        fuente[t] = "flujo_registrado+noflujo"
        print(f"  {t}: solo {len(sub)} datos -> servicio = flujo de los registros anteriores + atención sin flujo")
guardar("servicio_noflujo", df["noflujo"].clip(lower=1 / 60))
pd.DataFrame({"Observacion": np.arange(1, len(df) + 1), "wq_min": np.round(df["wq"], 4)}).to_csv(
    "datos/wq_real_pico.csv", index=False)
print(f"  datos/wq_real_pico.csv ({len(df)} datos)")

# ¿La atención sin flujo depende del tipo de vehículo? (justifica juntarla)
grupos = [g["noflujo"].to_numpy() for _, g in df.groupby("tipo") if len(g) >= 5]
if len(grupos) > 1:
    p = stats.kruskal(*grupos).pvalue
    print(f"\nKruskal-Wallis atención sin flujo entre tipos: p = {p:.4f} -> "
          + ("se puede usar una sola distribución" if p >= 0.05 else "DIFIERE por tipo: revisar antes de juntar"))

# Ventana de la muestra y llegadas
ini, fin = df["T1_s"].min() / 3600, df["T1_s"].max() / 3600
llegadas = []
for _, g in df.groupby("fecha"):
    llegadas.extend(np.diff(np.sort(g["T1_s"].to_numpy())) / 60)
llegadas = np.array([x for x in llegadas if x > 0])
guardar("entre_llegadas_pico", llegadas)
horas_obs = df.groupby("fecha")["T1_s"].agg(lambda s: (s.max() - s.min()) / 3600).sum()
lam = len(df) / horas_obs if horas_obs > 0 else float("nan")

print("\n========== RESUMEN DEL CICLO COMPLETO ==========")
print(f"Vehículos: {len(df)} | ventana {int(ini):02d}:{int(ini % 1 * 60):02d} a {int(fin):02d}:{int(fin % 1 * 60):02d} | λ ≈ {lam:.1f} veh/h")
print(df.groupby("tipo")[["wq", "flujo", "noflujo", "s_total"]].agg(["count", "mean"]).round(3).to_string())
print(f"\nWq real promedio = {df['wq'].mean():.3f} min ({df['wq'].mean()*60:.0f} s) | "
      f"{(df['wq'] < 1/60).mean()*100:.0f} % no esperó")
prop = df["tipo"].value_counts(normalize=True)
es = sum(prop.get(t, 0) * df.loc[df["tipo"] == t, "s_total"].mean() for t in prop.index)
print(f"Servicio total medio ponderado = {es:.3f} min")
for c in [2, 3]:
    print(f"Utilización teórica con {c} isleros = λ·E[S]/c = {lam/60*es/c*100:.1f} %")

json.dump({"ventana_pico": [float(ini), float(fin)], "fuente_servicio": fuente, "n": int(len(df)),
           "lambda_pico": float(lam), "wq_real_media": float(df["wq"].mean())},
          open("resultados/resumen_ciclo.json", "w", encoding="utf-8"), indent=2)
print("Guardado resultados/resumen_ciclo.json")
