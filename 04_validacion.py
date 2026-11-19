# -*- coding: utf-8 -*-
"""
SIMULACIÓN DE SISTEMAS - CECAR
Paso 4: VALIDACIÓN DEL MODELO BASE
(Basado en 04_validacion.py del profesor)

Como en campo no se registró la hora de inicio del servicio, el Wq real no se
puede medir. Se valida, como en el ejemplo del curso (piezas por turno), con
una medida observable en ambos sistemas:
    VEHÍCULOS ATENDIDOS POR HORA dentro de la ventana simulada.
El Wq se reporta como resultado del modelo y se contrasta con la fórmula
teórica de colas solo como referencia.

Archivos en datos/:
  datos_limpios.csv         -> lo genera 00 (de aquí sale el dato real)
  validacion_piloto.csv     -> 20 réplicas del Experimenter: Observacion, wq_min, veh_hora (+ pc1..pc4 opcional)
  validacion_corridas.csv   -> n réplicas, mismo formato
"""
import os
import json
import math
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
AZUL, NARANJA, GRIS = "#0F4C5C", "#E36414", "#6B7B83"
ALFA = 0.05
EPS_VEH = 3.0      # error máximo aceptado en vehículos/hora (± 3 veh/h)
EPS_WQ = 0.10      # error máximo aceptado en Wq (± 0.10 min = 6 s)
SERVIDORES = 2
TOLERANCIA = 5     # min: una hora cuenta como "observada completa" si la sesión la cubre con esta holgura

h0, h1 = config.VENTANA
print(f"Ventana simulada y validada: {h0:02d}:00 - {h1:02d}:00")


def leer(archivo):
    ruta = f"datos/{archivo}"
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
    col_veh = next(c for c in df.columns if "veh" in c)
    col_wq = "wq_min" if "wq_min" in df.columns else next(c for c in df.columns if c.startswith("wq"))
    return df[col_veh].dropna().to_numpy(), df[col_wq].dropna().to_numpy(), df


# ---------------------------------------------------------------------
# DATO REAL: vehículos por hora en horas observadas completas
# ---------------------------------------------------------------------
d = pd.read_csv("datos/datos_limpios.csv")
filas = []
for (fecha, ses), g in d.groupby(["fecha", "sesion"]):
    ini, fin = g["t_llegada"].min(), g["t_llegada"].max()
    for h in range(h0, h1):
        if ini <= h * 60 + TOLERANCIA and fin >= (h + 1) * 60 - TOLERANCIA:
            n = ((g["t_llegada"] >= h * 60) & (g["t_llegada"] < (h + 1) * 60)).sum()
            filas.append([fecha, h, n])
reales = pd.DataFrame(filas, columns=["fecha", "hora", "veh_hora"])
if reales.empty:
    raise SystemExit("No hay horas observadas completas dentro de la ventana. Cambie VENTANA en 05.")
reales.insert(0, "Observacion", range(1, len(reales) + 1))
reales.to_csv("datos/validacion_real.csv", index=False)
real = reales["veh_hora"].to_numpy()
print(f"Horas reales observadas completas en la ventana: {len(real)} (guardado datos/validacion_real.csv)")

veh_pil, wq_pil, _ = leer("validacion_piloto.csv")
veh_sim, wq_sim, df_sim = leer("validacion_corridas.csv")

# ---------------------------------------------------------------------
# PASOS 1 y 2 - Piloto y número de réplicas (se toma el mayor de las dos medidas)
# ---------------------------------------------------------------------
z = stats.norm.ppf(1 - ALFA / 2)
n0 = len(veh_pil)
n_veh = math.ceil((veh_pil.std(ddof=1) * z / EPS_VEH) ** 2)
n_wq = math.ceil((wq_pil.std(ddof=1) * z / EPS_WQ) ** 2)
n_req = max(n_veh, n_wq, n0)
print(f"\nPiloto n0 = {n0}")
print(f"  veh/h: media = {veh_pil.mean():.2f} | s = {veh_pil.std(ddof=1):.3f} | ε = {EPS_VEH} -> n = {n_veh}")
print(f"  Wq   : media = {wq_pil.mean():.3f} | s = {wq_pil.std(ddof=1):.4f} | ε = {EPS_WQ} -> n = {n_wq}")
print(f"  => Réplicas definitivas: n = {n_req}")
if len(veh_sim) < n_req:
    print(f"¡ATENCIÓN! validacion_corridas.csv tiene {len(veh_sim)} réplicas; se necesitan {n_req}.")

# ---------------------------------------------------------------------
# PASO 4 - Comparación real vs simulado (vehículos por hora)
# ---------------------------------------------------------------------
resumen = pd.DataFrame({
    "Real (por hora)": [len(real), real.mean(), real.var(ddof=1), real.std(ddof=1)],
    "Simulado (por réplica)": [len(veh_sim), veh_sim.mean(), veh_sim.var(ddof=1), veh_sim.std(ddof=1)],
}, index=["n", "Media (veh/h)", "Varianza", "Desv. estándar"])
print("\n", resumen.round(4))

v_sim, v_real = veh_sim.var(ddof=1), real.var(ddof=1)
F = v_sim / v_real
gl1, gl2 = len(veh_sim) - 1, len(real) - 1
p_F = 2 * min(stats.f.cdf(F, gl1, gl2), 1 - stats.f.cdf(F, gl1, gl2))
var_iguales = p_F >= ALFA
print(f"\nPrueba F: F = {F:.4f} | gl = ({gl1}, {gl2}) | p = {p_F:.4f} -> "
      + ("varianzas IGUALES" if var_iguales else "varianzas DIFERENTES (Welch)"))

res_t = stats.ttest_ind(veh_sim, real, equal_var=var_iguales)
t_crit = stats.t.ppf(1 - ALFA / 2, res_t.df)
ic = res_t.confidence_interval(confidence_level=1 - ALFA)
print(f"Prueba t ({'varianzas iguales' if var_iguales else 'Welch'}): t = {res_t.statistic:.4f} | "
      f"gl = {res_t.df:.1f} | t crítico = ±{t_crit:.4f} | p = {res_t.pvalue:.4f}")
print(f"IC 95 % μ(modelo) − μ(real): [{ic.low:.3f} ; {ic.high:.3f}] veh/h")

dif = veh_sim.mean() - real.mean()
z_cal = dif / math.sqrt(v_sim / len(veh_sim) + v_real / len(real))
p_z = 2 * (1 - stats.norm.cdf(abs(z_cal)))
print(f"Prueba z: z = {z_cal:.4f} | z crítico = ±{z:.3f} | p = {p_z:.4f}")
print(f"Diferencia relativa = {abs(dif) / real.mean() * 100:.2f} %")

if res_t.pvalue >= ALFA:
    print("\nNO se rechaza H0: el modelo atiende los mismos vehículos por hora que la estación -> MODELO VÁLIDO")
else:
    print("\nSe rechaza H0: el modelo difiere de la estación -> revisar llegadas, franjas y supuestos")

# ---------------------------------------------------------------------
# Validación complementaria: reparto de vehículos por cara (si se exportó PC1..PC4)
# ---------------------------------------------------------------------
cols_pc = [c for c in ["pc1", "pc2", "pc3", "pc4"] if c in df_sim.columns]
if len(cols_pc) == 4 and "cara" in d.columns:
    dv_c = d[(d["hora"] >= h0) & (d["hora"] < h1)]
    obs = dv_c["cara"].value_counts().reindex([1, 2, 3, 4]).fillna(0).to_numpy()
    esp_pct = df_sim[cols_pc].mean().to_numpy()
    esp = esp_pct / esp_pct.sum() * obs.sum()
    chi = stats.chisquare(obs, esp)
    print("\nReparto por cara (%):  real =", np.round(obs / obs.sum() * 100, 1),
          "| simulado =", np.round(esp_pct, 1))
    print(f"Chi² de bondad de ajuste: χ² = {chi.statistic:.3f} | gl = 3 | p = {chi.pvalue:.4f} -> "
          + ("el modelo reproduce el uso de las caras" if chi.pvalue >= ALFA else "el reparto por cara difiere"))

# ---------------------------------------------------------------------
# VALIDACIÓN DIRECTA DEL Wq (si se tomó la muestra del ciclo completo en hora pico)
# ---------------------------------------------------------------------
if os.path.exists("datos/wq_real_pico.csv") and "wq_pico" in df_sim.columns:
    wq_real = pd.read_csv("datos/wq_real_pico.csv")["wq_min"].to_numpy()
    wq_pico = df_sim["wq_pico"].dropna().to_numpy()
    print("\n=========== VALIDACIÓN DEL TIEMPO DE ESPERA (hora pico) ===========")
    print(f"Wq real   : media = {wq_real.mean():.4f} min ({wq_real.mean()*60:.1f} s) | n = {len(wq_real)} vehículos")
    print(f"Wq modelo : media = {wq_pico.mean():.4f} min ({wq_pico.mean()*60:.1f} s) | n = {len(wq_pico)} réplicas")
    vF = wq_pico.var(ddof=1) / wq_real.var(ddof=1)
    g1, g2 = len(wq_pico) - 1, len(wq_real) - 1
    pF = 2 * min(stats.f.cdf(vF, g1, g2), 1 - stats.f.cdf(vF, g1, g2))
    igual = pF >= ALFA
    rt = stats.ttest_ind(wq_pico, wq_real, equal_var=igual)
    ict = rt.confidence_interval(confidence_level=1 - ALFA)
    print(f"Prueba F: F = {vF:.4f} | p = {pF:.4f} -> " + ("varianzas iguales" if igual else "varianzas diferentes (Welch)"))
    print(f"Prueba t: t = {rt.statistic:.4f} | gl = {rt.df:.1f} | p = {rt.pvalue:.4f} | "
          f"IC 95 % de la diferencia: [{ict.low:.4f} ; {ict.high:.4f}] min")
    print("=> " + ("NO se rechaza H0: el modelo reproduce la espera real en hora pico" if rt.pvalue >= ALFA
                   else "Se rechaza H0: la espera simulada difiere de la real -> revisar tiempos de servicio y llegadas"))
    if "veh_hora_pico" in df_sim.columns and os.path.exists("resultados/resumen_ciclo.json"):
        lp = json.load(open("resultados/resumen_ciclo.json", encoding="utf-8"))["lambda_pico"]
        print(f"Vehículos/hora en la ventana pico: modelo = {df_sim['veh_hora_pico'].mean():.1f} | muestra real = {lp:.1f}")

# ---------------------------------------------------------------------
# Wq del modelo (resultado) y referencia teórica
# ---------------------------------------------------------------------
ic_wq = stats.t.interval(1 - ALFA, len(wq_sim) - 1, loc=wq_sim.mean(),
                         scale=wq_sim.std(ddof=1) / np.sqrt(len(wq_sim)))
print(f"\nWq simulado = {wq_sim.mean():.4f} min | IC 95 %: [{ic_wq[0]:.4f} ; {ic_wq[1]:.4f}]")

dv = d[(d["hora"] >= h0) & (d["hora"] < h1)]
entre = dv["entre_llegadas"].dropna().to_numpy()
serv = dv["servicio"].to_numpy().copy()
for t, (a, m_, b) in getattr(config, "SERVICIO_EXPERTO", {}).items():   # mismo supuesto del modelo
    mask = (dv["tipo"] == t).to_numpy()
    serv[mask] = np.random.default_rng(config.SEMILLA).triangular(a, m_, b, mask.sum()) / 60
lam, mu = 1 / entre.mean(), 1 / serv.mean()
c, a = SERVIDORES, lam / mu
rho = a / c
ca2, cs2 = entre.var(ddof=1) / entre.mean() ** 2, serv.var(ddof=1) / serv.mean() ** 2
print(f"Datos reales de la ventana: λ = {lam*60:.2f} veh/h | μ = {mu*60:.2f} veh/h por islero | "
      f"ρ = {rho:.3f} | Ca² = {ca2:.3f} | Cs² = {cs2:.3f}")
if rho < 1:
    suma = sum(a ** k / math.factorial(k) for k in range(c))
    ult = a ** c / math.factorial(c) / (1 - rho)
    wq_mmc = (ult / (suma + ult)) / (c * mu - lam)
    wq_ggc = wq_mmc * (ca2 + cs2) / 2
    print(f"Wq teórico M/M/{c} = {wq_mmc:.4f} min | G/G/{c} (Allen-Cunneen) = {wq_ggc:.4f} min")
    print("  Referencia en estado estable; no captura islas fijas ni la variación horaria.")
else:
    print("ρ ≥ 1 en promedio: la fórmula de estado estable no aplica.")

# ---------------------------------------------------------------------
# Gráfico
# ---------------------------------------------------------------------
fig, axs = plt.subplots(1, 2, figsize=(10, 4.4), gridspec_kw={"width_ratios": [1.1, 1]})
bp = axs[0].boxplot([real, veh_sim], widths=0.5, patch_artist=True, medianprops=dict(color="black", linewidth=2))
for caja, color in zip(bp["boxes"], [AZUL, NARANJA]):
    caja.set_facecolor(color); caja.set_alpha(0.75)
axs[0].set_xticks([1, 2], ["Real", "Simulado"]); axs[0].set_ylabel("Vehículos atendidos por hora")
axs[0].set_title("Distribución de los resultados", loc="left")
medias = [real.mean(), veh_sim.mean()]
err = [stats.t.ppf(0.975, len(m) - 1) * m.std(ddof=1) / np.sqrt(len(m)) for m in (real, veh_sim)]
axs[1].errorbar([0, 1], medias, yerr=err, fmt="o", ms=9, capsize=8, color=GRIS, ecolor=GRIS)
axs[1].scatter([0, 1], medias, s=90, color=[AZUL, NARANJA], zorder=3)
axs[1].set_xticks([0, 1], ["Real", "Simulado"]); axs[1].set_xlim(-0.6, 1.6)
axs[1].set_title("Medias con IC 95 %", loc="left")
for i, m in enumerate(medias):
    axs[1].annotate(f"{m:.2f}", (i + 0.12, m), va="center")
for ax in axs:
    ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout(); plt.savefig("figuras/04_validacion.png", dpi=200); plt.show()