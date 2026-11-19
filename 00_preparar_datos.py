# -*- coding: utf-8 -*-
"""
SIMULACIÓN DE SISTEMAS - CECAR
Paso 0: PREPARAR LOS DATOS DE CAMPO

Columnas esperadas del CSV de campo:
  Fecha, Hora, Franja_Horaria, Isla, Cara, Vehiculo, Producto, Galones, Valor, Tiempo_Servicio_seg
  ('Hora' = hora de LLEGADA del vehículo)

Genera en datos/:
  datos_limpios.csv                  -> base depurada (la usan 00b, 04 y 05)
  entre_llegadas.csv                 -> tiempo entre llegadas global (min)
  servicio_moto.csv / _carro / _camion   (min)
  servicio_<tipo>_gasolina / _acpm   -> solo si el producto cambia el tiempo de servicio
Y en resultados/:
  resumen_campo.json                 -> proporciones de vehículo y producto para FlexSim
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

# =====================================================================
# CONFIGURACIÓN
# =====================================================================
ARCHIVO_CAMPO = "datos/datos_campo.csv"
COL_FECHA, COL_HORA, COL_FRANJA = "Fecha", "Hora", "Franja_Horaria"
COL_ISLA, COL_CARA = "Isla", "Cara"
COL_VEH, COL_PROD = "Vehiculo", "Producto"
COL_GAL, COL_SERV = "Galones", "Tiempo_Servicio_seg"
CORTE_SESION_MIN = 30   # si entre dos llegadas pasan más de 30 min, se asume que se dejó de observar
ALFA = 0.05
rng = np.random.default_rng(config.SEMILLA)
# =====================================================================

# ---------- Lectura (detecta ; , o tabulación y quita el BOM) ----------
with open(ARCHIVO_CAMPO, encoding="utf-8-sig") as fh:
    encabezado = fh.readline()
sep = next((d for d in [";", "\t", ","] if d in encabezado), ",")
df = pd.read_csv(ARCHIVO_CAMPO, sep=sep, encoding="utf-8-sig")
df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
print("Columnas encontradas:", list(df.columns))
print("Filas leídas:", len(df))
faltan = [c for c in [COL_FECHA, COL_HORA, COL_VEH, COL_PROD, COL_SERV] if c not in df.columns]
if faltan:
    raise SystemExit(f"Faltan columnas: {faltan}. Ajuste los nombres en CONFIGURACIÓN.")


def a_minutos_del_dia(serie):
    """Convierte la hora a minutos desde las 00:00. Acepta 14:05:30, 14:05, 2:05:30 p. m., fracción Excel."""
    s = serie.astype(str).str.strip().str.lower()
    s = s.str.replace(r"a\.?\s*m\.?", " AM", regex=True).str.replace(r"p\.?\s*m\.?", " PM", regex=True)
    s = s.str.replace(r"\s+", " ", regex=True).str.strip()
    num = pd.to_numeric(s.str.replace(",", "."), errors="coerce")
    if num.notna().all() and (num < 1).all():
        return num * 1440
    res = pd.Series(np.nan, index=s.index)
    for fmt in ["%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"]:
        t = pd.to_datetime(s, format=fmt, errors="coerce")
        m = t.dt.hour * 60 + t.dt.minute + t.dt.second / 60
        res = res.fillna(m)
    if res.isna().any():  # último intento: fecha y hora juntas
        t = pd.to_datetime(s[res.isna()], errors="coerce", dayfirst=True)
        res = res.fillna(t.dt.hour * 60 + t.dt.minute + t.dt.second / 60)
    if res.isna().any():
        raise SystemExit(f"No se pudieron leer estas horas: {serie[res.isna()].head().tolist()}")
    return res


def tipo_vehiculo(v):
    v = str(v).strip().lower()
    if "moto" in v or "frasco" in v or "galon" in v or "pimpina" in v:
        return "moto"   # compra pequeña (moto o recipiente): servicio corto equivalente
    if any(k in v for k in ["cami", "bus", "volqueta", "tracto", "turbo", "bioacem", "pesado"]) and "camioneta" not in v:
        return "camion"
    if any(k in v for k in ["carro", "auto", "camioneta", "taxi", "campero", "jeep", "particular"]):
        return "carro"
    return "otro"


def producto(v):
    v = str(v).strip().lower()
    if any(k in v for k in ["acpm", "diesel", "diésel", "bio"]):
        return "acpm"
    if any(k in v for k in ["gasolina", "corriente", "extra", "gas"]):
        return "gasolina"
    return "otro"


df["fecha"] = df[COL_FECHA].astype(str).str.strip()
df["t_llegada"] = a_minutos_del_dia(df[COL_HORA])
df["tipo"] = df[COL_VEH].map(tipo_vehiculo)
df["producto"] = df[COL_PROD].map(producto)
df["servicio"] = pd.to_numeric(df[COL_SERV].astype(str).str.replace(",", "."), errors="coerce") / 60

print("\nClasificación de vehículos (revise que esté bien):")
print(df.groupby([COL_VEH, "tipo"]).size().to_string())
print("\nClasificación de productos:")
print(df.groupby([COL_PROD, "producto"]).size().to_string())

malas = df[(df["tipo"] == "otro") | (df["producto"] == "otro") | df["servicio"].isna() | (df["servicio"] <= 0)]
if len(malas):
    print(f"\n¡ATENCIÓN! {len(malas)} filas excluidas (tipo/producto no reconocido o servicio inválido):")
    print(malas[[COL_FECHA, COL_HORA, COL_VEH, COL_PROD, COL_SERV]].head(15).to_string())
    df = df.drop(malas.index)

n_frasco = df[COL_VEH].astype(str).str.lower().str.contains("frasco|galon|pimpina").sum()
if n_frasco:
    print(f"\nNota: {n_frasco} compras en recipiente (frasco) se agrupan con las motos por su servicio corto.")

if COL_CARA in df.columns:
    df["cara_num"] = pd.to_numeric(df[COL_CARA].astype(str).str.extract(r"(\d+)")[0], errors="coerce")

# ---------- Corrección por redondeo de los registros ----------
# Hora de llegada: si se anotó solo hora:minuto, la llegada real ocurrió en algún
# instante dentro de ese minuto -> se reparte uniformemente en [0, 1) min.
seg = np.round((df["t_llegada"] * 60) % 60)
if (seg == 0).all():
    print("\nLas horas de llegada están en minutos exactos (sin segundos).")
    if config.CORREGIR_REDONDEO:
        df["t_llegada"] = df["t_llegada"] + rng.uniform(0, 1, len(df))
        print("  CORRECCIÓN: cada llegada se repartió uniformemente dentro de su minuto (U[0, 1) min).")
        print("  Esto evita tiempos entre llegadas iguales a 0 y en múltiplos exactos de 1 min.")
    else:
        print("  Sin corrección: habrá muchos ceros y valores enteros (afecta independencia y ajuste).")

# Tiempo de servicio: se detecta la resolución del registro (1, 5, 10 s...) por tipo
servicio_constante = {}
seg_serv = df["servicio"] * 60
for t in ["moto", "carro", "camion"]:
    m = df["tipo"] == t
    if m.sum() == 0:
        continue
    vals = np.round(seg_serv[m]).astype(int)
    if vals.nunique() == 1:
        servicio_constante[t] = float(vals.iloc[0]) / 60
        print(f"\nTodos los servicios de '{t}' se anotaron con el valor típico de {vals.iloc[0]} s.")
        if t in getattr(config, "SERVICIO_EXPERTO", {}):
            a, m_, b = config.SERVICIO_EXPERTO[t]
            print(f"  En el modelo se usará Triangular(mín={a}, moda={m_}, máx={b}) s, definida en config.py.")
        else:
            print("  Se modelará como CONSTANTE. Defina su rango en config.SERVICIO_EXPERTO si lo conoce.")
        continue
    res = max([r for r in [1, 2, 5, 10, 15, 30] if (vals % r == 0).all()] or [1])
    if config.CORREGIR_REDONDEO:
        df.loc[m, "servicio"] = np.maximum((vals + rng.uniform(-res / 2, res / 2, m.sum())) / 60, 1 / 60)
        print(f"Servicio '{t}': registrado con resolución de {res} s -> CORRECCIÓN U(-{res/2:g}, {res/2:g}) s")

# ---------- Sesiones de observación y tiempo entre llegadas ----------
df = df.sort_values(["fecha", "t_llegada"]).reset_index(drop=True)
df["sesion"] = 0
df["entre_llegadas"] = np.nan
sid = 0
for _, g in df.groupby("fecha", sort=False):
    dif = g["t_llegada"].diff()
    nueva = dif.isna() | (dif > CORTE_SESION_MIN)
    ids = sid + nueva.cumsum()
    sid = ids.max()
    df.loc[g.index, "sesion"] = ids
    df.loc[g.index, "entre_llegadas"] = dif.where(~nueva)

ceros = int((df["entre_llegadas"] <= 0).sum())
if ceros:
    print(f"\nNota: {ceros} llegadas registradas a la misma hora; su tiempo entre llegadas (0) se reemplaza por 1 s.")
    df.loc[df["entre_llegadas"] <= 0, "entre_llegadas"] = 1 / 60

df["hora"] = np.floor(df["t_llegada"] / 60).astype(int)

# ---------- Guardar archivos de variables ----------
def guardar(nombre, valores):
    valores = np.asarray(valores, dtype=float)
    pd.DataFrame({"tiempo_min": np.round(valores, 4)}).to_csv(f"datos/{nombre}.csv", index=False)
    aviso = "  <- menos de 30 datos" if len(valores) < 30 else ""
    print(f"  datos/{nombre}.csv ({len(valores)} datos){aviso}")


print("\nArchivos generados:")
guardar("entre_llegadas", df["entre_llegadas"].dropna())

config_servicio = {}
for t in ["moto", "carro", "camion"]:
    sub = df[df["tipo"] == t]
    if len(sub) == 0:
        continue
    guardar(f"servicio_{t}", sub["servicio"])
    if t in servicio_constante:
        config_servicio[t] = {"gasolina": f"servicio_{t}", "acpm": f"servicio_{t}"}
        continue
    config_servicio[t] = {"gasolina": f"servicio_{t}", "acpm": f"servicio_{t}"}
    g, a = sub.loc[sub["producto"] == "gasolina", "servicio"], sub.loc[sub["producto"] == "acpm", "servicio"]
    if len(g) >= 30 and len(a) >= 30:
        p = stats.mannwhitneyu(g, a, alternative="two-sided").pvalue
        if p < ALFA:
            print(f"  -> En {t}, el producto SÍ cambia el tiempo de servicio (Mann-Whitney p = {p:.4f}): se separa")
            guardar(f"servicio_{t}_gasolina", g)
            guardar(f"servicio_{t}_acpm", a)
            config_servicio[t] = {"gasolina": f"servicio_{t}_gasolina", "acpm": f"servicio_{t}_acpm"}
        else:
            print(f"  -> En {t}, gasolina y ACPM tienen tiempos similares (p = {p:.4f}): se usa una sola distribución")

df_out = df[["fecha", "sesion", "hora", "t_llegada", "entre_llegadas", "tipo", "producto", "servicio"]].copy()
if "cara_num" in df.columns:
    df_out["cara"] = df["cara_num"].values
for col, nuevo in [(COL_FRANJA, "franja_campo"), (COL_ISLA, "isla"), (COL_GAL, "galones")]:
    if col in df.columns:
        df_out[nuevo] = df[col].values
df_out.to_csv("datos/datos_limpios.csv", index=False)
print("  datos/datos_limpios.csv")

# ---------- Resumen ----------
prop = df["tipo"].value_counts(normalize=True).reindex(["moto", "carro", "camion"]).fillna(0)
p_acpm = df.groupby("tipo")["producto"].apply(lambda s: (s == "acpm").mean()).reindex(["moto", "carro", "camion"]).fillna(0)
obs_h = df.groupby("sesion")["t_llegada"].agg(lambda s: s.max() - s.min()).sum() / 60
lam = 60 / df["entre_llegadas"].mean()

print("\n========== RESUMEN DEL SISTEMA REAL ==========")
print(f"Vehículos: {len(df)} | días: {df['fecha'].nunique()} | sesiones: {df['sesion'].nunique()} | "
      f"horas observadas: {obs_h:.1f}")
print(f"Tasa de llegada global λ = {lam:.2f} veh/h")
print("Proporción por tipo y % de ACPM dentro de cada tipo:")
for t in ["moto", "carro", "camion"]:
    print(f"  {t:7s}: {prop[t]*100:5.1f} % de los vehículos | ACPM = {p_acpm[t]*100:5.1f} %")
print("\nTiempo de servicio (min) por tipo y producto:")
print(df.groupby(["tipo", "producto"])["servicio"].agg(["count", "mean", "std", "min", "max"]).round(3).to_string())
cara_por_tipo, cara_global = {}, None
if "cara" in df_out.columns:
    tab = pd.crosstab(df_out["tipo"], df_out["cara"], normalize="index").reindex(columns=[1, 2, 3, 4], fill_value=0)
    cara_global = (df_out["cara"].value_counts(normalize=True).reindex([1, 2, 3, 4]).fillna(0)).tolist()
    cara_por_tipo = {t: [float(v) for v in tab.loc[t]] for t in tab.index}
    print("\nReparto real por cara (%) — el modelo lo usa para elegir cara y luego se valida:")
    print((tab * 100).round(1).to_string())
    print("Global:", [round(v * 100, 1) for v in cara_global])

json.dump({
    "proporcion_tipo": {t: float(prop[t]) for t in prop.index},
    "prob_acpm": {t: float(p_acpm[t]) for t in p_acpm.index},
    "config_servicio": config_servicio,
    "lambda_global_veh_h": float(lam),
    "servicio_constante": servicio_constante,
    "cara_por_tipo": cara_por_tipo,
    "cara_global": cara_global,
}, open("resultados/resumen_campo.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("\nGuardado resultados/resumen_campo.json")
