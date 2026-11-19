# -*- coding: utf-8 -*-
"""
SIMULACIÓN DE SISTEMAS - CECAR
Paso 5: GENERAR EL CONSTRUCTOR DEL MODELO EN FLEXSIM

Lee lo que dejaron 00, 00b y 03 en resultados/ y escribe
  construir_modelo.fs   -> se pega en FlexSim (View > Script Console > Execute)
  resultados/config_modelo.json -> ventana simulada (la usa 04 para validar)

Si aún no hay ajustes, usa valores PROVISIONALES y lo avisa.
"""
import os
import json
import config

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    pass
os.makedirs("resultados", exist_ok=True)

# =====================================================================
# CONFIGURACIÓN DEL EXPERIMENTO
# =====================================================================
VENTANA = config.VENTANA   # se cambia en config.py
WARMUP = config.WARMUP
VEL_ISLERO = 60            # m/min (= 1 m/s)
# =====================================================================

provisional = []
pre = {"lleg": "", "serv": ""}      # código previo (arreglos de las distribuciones empíricas)
n_emp = [0]


def empirica(variable, contexto):
    """Distribución empírica continua (interpolación lineal entre los datos ordenados)."""
    import pandas as pd
    datos = sorted(pd.read_csv(f"datos/{variable}.csv")["tiempo_min"].round(4).tolist())
    n_emp[0] += 1
    k = n_emp[0]
    pre[contexto] += (f"Array e{k} = [{', '.join(f'{v:g}' for v in datos)}];\n"
                      f"double u{k} = uniform(0, e{k}.length - 1, getstream(current));\n"
                      f"int i{k} = Math.floor(u{k});\n"
                      f"if (i{k} > e{k}.length - 2) i{k} = e{k}.length - 2;\n")
    print(f"  {variable:38s} -> EMPÍRICA    {len(datos)} datos, de {datos[0]:.3f} a {datos[-1]:.3f} min")
    return f"(e{k}[i{k} + 1] + (u{k} - i{k}) * (e{k}[i{k} + 2] - e{k}[i{k} + 1]))"


def expresion(variable, defecto, contexto="serv"):
    if variable in getattr(config, "USAR_EMPIRICA", []) and os.path.exists(f"datos/{variable}.csv"):
        return empirica(variable, contexto)
    ruta = f"resultados/ajuste_{variable}.json"
    if os.path.exists(ruta):
        d = json.load(open(ruta, encoding="utf-8"))
        print(f"  {variable:38s} -> {d['distribucion']:11s} {d['flexsim']}")
        return d["flexsim"]
    provisional.append(variable)
    print(f"  {variable:38s} -> PROVISIONAL  {defecto}")
    return defecto


print("Expresiones que se usan en el modelo:")
inicio_min = VENTANA[0] * 60 - WARMUP
HORA = f"fmod(({inicio_min} + Model.time) / 60, 24)"

# ---------- Llegadas (por franja si existe 00b) ----------
if os.path.exists("resultados/franjas.json"):
    franjas = sorted(json.load(open("resultados/franjas.json", encoding="utf-8")), key=lambda f: f["h_ini"])
    franjas = [f for f in franjas if f["h_fin"] > VENTANA[0] and f["h_ini"] < VENTANA[1]] or franjas
    partes = [(f["h_fin"], expresion(f["variable"], f"exponential(0, {60/f['lambda_veh_h']:.4f}, getstream(current))", "lleg"))
              for f in franjas]
    exp_lleg = partes[-1][1]
    for h_fin, e in reversed(partes[:-1]):
        exp_lleg = f"({HORA} < {h_fin} ? {e} : {exp_lleg})"
else:
    exp_lleg = expresion("entre_llegadas", "exponential(0, 0.6452, getstream(current))", "lleg")

# ---------- Proporciones ----------
if os.path.exists("resultados/resumen_campo.json"):
    rc = json.load(open("resultados/resumen_campo.json", encoding="utf-8"))
    pt, pa, cfg = rc["proporcion_tipo"], rc["prob_acpm"], rc["config_servicio"]
    cpt = rc.get("cara_por_tipo") or {}
else:
    provisional.append("proporciones")
    pt = {"moto": 0.60, "carro": 0.35, "camion": 0.05}
    pa = {"moto": 0.0, "carro": 0.20, "camion": 0.90}
    cfg = {t: {"gasolina": f"servicio_{t}", "acpm": f"servicio_{t}"} for t in ["moto", "carro", "camion"]}
    cpt = {}
pesos = {t: cpt.get(t, [0.25, 0.25, 0.25, 0.25]) for t in ["moto", "carro", "camion"]}
print("Preferencia de cara (%) por tipo [C1, C2, C3, C4]:")
for t in pesos:
    print(f"  {t:7s}", [round(v * 100, 1) for v in pesos[t]])
lim_moto = round(pt["moto"] * 100)
lim_carro = round((pt["moto"] + pt["carro"]) * 100)

# ---------- Servicio ----------
defecto_serv = {"moto": "uniform(0.0833, 0.3333, getstream(current))",
                "carro": "uniform(1.0, 2.0, getstream(current))",
                "camion": "uniform(3.0, 13.33, getstream(current))"}
serv = {}
experto = getattr(config, "SERVICIO_EXPERTO", {})
ciclo = json.load(open("resultados/resumen_ciclo.json", encoding="utf-8")) if os.path.exists("resultados/resumen_ciclo.json") else None
exp_noflujo = None
if ciclo:
    print("  (se usan los datos del CICLO COMPLETO tomados en hora pico)")
    if any(v != "total" for v in ciclo["fuente_servicio"].values()):
        exp_noflujo = expresion("servicio_noflujo", "uniform(0.3, 1.0, getstream(current))")
for t in ["moto", "carro", "camion"]:
    if ciclo and ciclo["fuente_servicio"].get(t) == "total":
        e = expresion(f"servicio_total_{t}", defecto_serv[t])
        serv[(t, "g")] = serv[(t, "a")] = e
        continue
    if t in experto:   # triangular por criterio experto (segundos -> minutos)
        a, m_, b = [v / 60 for v in experto[t]]
        e = f"triangular({a:.4f}, {b:.4f}, {m_:.4f}, getstream(current))"
        print(f"  servicio_{t:32s} -> Triangular  {e}  (criterio experto, config.py)")
        serv[(t, "g")] = serv[(t, "a")] = e
        continue
    c = cfg.get(t, {"gasolina": f"servicio_{t}", "acpm": f"servicio_{t}"})
    serv[(t, "g")] = expresion(c["gasolina"], defecto_serv[t])
    serv[(t, "a")] = serv[(t, "g")] if c["acpm"] == c["gasolina"] else expresion(c["acpm"], defecto_serv[t])


if ciclo and exp_noflujo:
    for t in ["moto", "carro", "camion"]:
        if ciclo["fuente_servicio"].get(t) != "total":
            for pr in ["g", "a"]:
                serv[(t, pr)] = f"({serv[(t, pr)]}) + ({exp_noflujo})"
            print(f"  servicio {t:31s} -> flujo registrado + atención sin flujo")

# Muestra de hora pico (00d): multitarea del islero en carros y camiones
muestra = None
if not ciclo and os.path.exists("resultados/muestra_pico.json"):
    muestra = json.load(open("resultados/muestra_pico.json", encoding="utf-8"))
multitarea = 1 if muestra else 0
exp_cobro = "0"
exp_prep_sep = "0"
prep = getattr(config, "PREPARACION_S", None)
exp_prep = f" + triangular({prep[0]/60:.4f}, {prep[2]/60:.4f}, {prep[1]/60:.4f}, getstream(current))" if prep else ""
if muestra:
    a, m_, b = [v / 60 for v in muestra["tri_moto_s"]]
    prep_moto = ""
    if prep:
        exp_prep_sep = f"triangular({prep[0]/60:.4f}, {prep[2]/60:.4f}, {prep[1]/60:.4f}, getstream(current))"
    elif muestra.get("prep_moto_estimada_s") and getattr(config, "USAR_PREPARACION_ESTIMADA", True):
        pe = muestra["prep_moto_estimada_s"] / 60
        exp_prep_sep = f"triangular({0.5*pe:.4f}, {1.5*pe:.4f}, {pe:.4f}, getstream(current))"
        prep_moto = "estimada"
        print(f"    preparación ESTIMADA por la ráfaga (pedir el monto y programar el surtidor): media {muestra['prep_moto_estimada_s']:.1f} s")
    else:
        exp_prep_sep = "0"
    exp_prep = ""   # la preparación ahora va aparte (EXP_PREP) para poder medir la espera hasta la manguera
    e = f"triangular({a:.4f}, {b:.4f}, {m_:.4f}, getstream(current))"
    serv[("moto", "g")] = serv[("moto", "a")] = e
    a, m_, b = [v / 60 for v in muestra["tri_cobro_s"]]
    exp_cobro = f"triangular({a:.4f}, {b:.4f}, {m_:.4f}, getstream(current)){exp_prep}"
    print("  MULTITAREA (muestra de hora pico):")
    print(f"    moto: islero ocupado todo el servicio -> {e}")
    print(f"    carro y camión: islero ocupado solo en el cobro -> {exp_cobro}; el surtidor sigue solo durante el flujo")
    if not prep and not prep_moto:
        print("    (sin tiempo de preparación: defina PREPARACION_S en config.py cuando lo tenga)")
    elif not prep:
        print("    (preparación de moto ESTIMADA; reemplácela por PREPARACION_S cuando la midan)")

if muestra and muestra.get("media_entre_llegadas_pico_min") and getattr(config, "USAR_LLEGADAS_PICO_CAMPO", True):
    h_a, h_b = muestra["ventana_pico"]
    mpico = muestra["media_entre_llegadas_pico_min"]
    exp_lleg = f"(({HORA} >= {h_a:.4f} && {HORA} < {h_b:.4f}) ? exponential(0, {mpico:.4f}, getstream(current)) : {exp_lleg})"
    print(f"  Llegadas de {int(h_a):02d}:{int(h_a%1*60):02d} a {int(h_b):02d}:{int(h_b%1*60):02d}: medidas en campo, "
          f"≈ {60/mpico:.0f} veh/h (exponencial, media {mpico*60:.1f} s)")
    # se reemplaza en los parámetros que ya se habían armado
# Ventana pico (para comparar con el Wq real medido en campo), en minutos de reloj del modelo
fuente_pico = ciclo or muestra
if fuente_pico:
    pico_ini = fuente_pico["ventana_pico"][0] * 60 - inicio_min
    pico_fin = fuente_pico["ventana_pico"][1] * 60 - inicio_min
else:
    pico_ini = pico_fin = -1


def fs(s):  # texto Python -> literal de cadena FlexScript
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


duracion = (VENTANA[1] - VENTANA[0]) * 60
parametros = f"""string PRE_LLEGADAS = {fs(pre['lleg'])};
string PRE_SERVICIO = {fs(pre['serv'])};
string EXP_LLEGADAS = {fs(exp_lleg)};
string EXP_MOTO_G   = {fs(serv[('moto', 'g')])};
string EXP_MOTO_A   = {fs(serv[('moto', 'a')])};
string EXP_CARRO_G  = {fs(serv[('carro', 'g')])};
string EXP_CARRO_A  = {fs(serv[('carro', 'a')])};
string EXP_CAMION_G = {fs(serv[('camion', 'g')])};
string EXP_CAMION_A = {fs(serv[('camion', 'a')])};
string LIM_MOTO  = "{lim_moto}";       // 1..{lim_moto} -> moto
string LIM_CARRO = "{lim_carro}";      // ..{lim_carro} -> carro ; resto -> camión
string P_ACPM_MOTO   = "{pa['moto']*100:.1f}";   // % de motos que tanquean ACPM
string P_ACPM_CARRO  = "{pa['carro']*100:.1f}";
string P_ACPM_CAMION = "{pa['camion']*100:.1f}";
string WARMUP   = "{WARMUP}";
string DURACION = "{duracion}";        // min de la ventana {VENTANA[0]:02d}:00-{VENTANA[1]:02d}:00
double VEL_ISLERO = {VEL_ISLERO};
int MULTITAREA = {multitarea};          // 1 = en carros y camiones el islero se libera durante el flujo
string EXP_COBRO = {fs(exp_cobro)};
string EXP_PREP  = {fs(exp_prep_sep)};   // pedir el monto, programar el surtidor y poner la manguera (todos los vehículos)
string PICO_INI = "{pico_ini:.2f}";    // ventana de la muestra del ciclo completo (min de modelo)
string PICO_FIN = "{pico_fin:.2f}";
string W_MOTO   = "[{', '.join(f'{v*100:.1f}' for v in pesos['moto'])}]";     // % de preferencia por cara 1..4
string W_CARRO  = "[{', '.join(f'{v*100:.1f}' for v in pesos['carro'])}]";
string W_CAMION = "[{', '.join(f'{v*100:.1f}' for v in pesos['camion'])}]";"""

plantilla = open("plantilla_modelo.fs", encoding="utf-8").read() if os.path.exists("plantilla_modelo.fs") else None
if plantilla is None:
    raise SystemExit("Falta plantilla_modelo.fs en la carpeta del proyecto.")
estado = ("VALORES PROVISIONALES en: " + ", ".join(provisional)) if provisional else "valores ajustados con los datos de campo"
salida = plantilla.replace("@@PARAMETROS@@", parametros).replace("@@ESTADO@@", estado) \
    .replace("@@RUNTIME@@", str(WARMUP + duracion)).replace("@@VENTANA@@", f"{VENTANA[0]:02d}:00-{VENTANA[1]:02d}:00")
open("construir_modelo.fs", "w", encoding="utf-8").write(salida)
json.dump({"ventana": list(VENTANA), "warmup_min": WARMUP, "run_time_min": WARMUP + duracion},
          open("resultados/config_modelo.json", "w", encoding="utf-8"), indent=2)

print(f"\nGenerado construir_modelo.fs ({estado})")
print(f"Run Time del Experimenter = {WARMUP + duracion} min  (Warmup del Experimenter = 0)")
