# -*- coding: utf-8 -*-
"""
SIMULACIÓN DE SISTEMAS - CECAR
Fase 3 - Paso 3: BONDAD DE AJUSTE (AUTOMATIZADO)
"""
import os
import json
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
os.makedirs("resultados", exist_ok=True)
AZUL, NARANJA, GRIS = "#0F4C5C", "#E36414", "#6B7B83"
COLORES = [NARANJA, AZUL, "#5B8E7D", "#9A348E", "#B08D57", GRIS]
ALFA = 0.05


# Analiza automáticamente todos los archivos que generan 00 y 00b
# (entre_llegadas*, servicio_*), con la columna tiempo_min en MINUTOS
VARIABLES = sorted(f[:-4] for f in os.listdir(CARPETA_DATOS)
                   if f.endswith(".csv") and f.startswith(("entre_llegadas", "servicio_")))
print("Variables a analizar:", VARIABLES)

def ajustar(nombre, x, COTA_INF, DELTA):
    if nombre == "Normal":
        m, s = stats.norm.fit(x)
        return stats.norm(m, s), f"μ={m:.3f}, σ={s:.3f}", 2
    if nombre == "Exponencial":
        loc, esc = stats.expon.fit(x, floc=COTA_INF)
        return stats.expon(loc, esc), f"media={esc:.3f}", 1
    if nombre == "Gamma":
        a, loc, esc = stats.gamma.fit(x, floc=COTA_INF)
        return stats.gamma(a, loc, esc), f"α={a:.3f}, β={esc:.3f}", 2
    if nombre == "Erlang":
        a, loc, esc = stats.gamma.fit(x, floc=COTA_INF)
        k = max(1, int(round(a)))
        esc = (x.mean() - COTA_INF) / k
        return stats.gamma(k, COTA_INF, esc), f"k={k}, β={esc:.3f}", 2
    if nombre == "Lognormal":
        s, loc, esc = stats.lognorm.fit(x, floc=COTA_INF)
        return stats.lognorm(s, loc, esc), f"μ={np.log(esc):.3f}, σ={s:.3f}", 2
    if nombre == "Weibull":
        c, loc, esc = stats.weibull_min.fit(x, floc=COTA_INF)
        return stats.weibull_min(c, loc, esc), f"forma={c:.3f}, escala={esc:.3f}", 2
    if nombre == "Beta":
        a_, b_ = COTA_INF, x.max() + 0.05 * (x.max() - x.min())
        p, q, loc, esc = stats.beta.fit(x, floc=a_, fscale=b_ - a_)
        return stats.beta(p, q, loc, esc), f"p={p:.3f}, q={q:.3f}", 2   # EDITADO: límites fijos -> solo p y q se estiman
    if nombre == "Triangular":
        a_, b_ = max(COTA_INF, x.min() - DELTA), x.max() + DELTA
        c, loc, esc = stats.triang.fit(x, floc=a_, fscale=b_ - a_)
        moda = a_ + c * (b_ - a_)
        return stats.triang(c, a_, b_ - a_), f"mín={a_:.2f}, moda={moda:.2f}, máx={b_:.2f}", 3
    if nombre == "Uniforme":
        a_, b_ = max(COTA_INF, x.min() - DELTA), x.max() + DELTA
        return stats.uniform(a_, b_ - a_), f"mín={a_:.2f}, máx={b_:.2f}", 2
    if nombre == "Logística":
        m, s = stats.logistic.fit(x)
        return stats.logistic(m, s), f"μ={m:.3f}, s={s:.3f}", 2

def chi_cuadrado(dist, n_par, x, n):
    k = int(round(1 + 3.322 * np.log10(n)))
    limites = dist.ppf(np.linspace(0, 1, k + 1))
    limites[0], limites[-1] = -np.inf, np.inf
    obs, _ = np.histogram(x, bins=limites)
    esp = np.full(k, n / k)
    chi2 = np.sum((obs - esp) ** 2 / esp)
    gl = k - 1 - n_par
    p = 1 - stats.chi2.cdf(chi2, gl) if gl > 0 else np.nan
    return chi2, gl, p

def kolmogorov_smirnov(dist, x):
    res = stats.kstest(x, dist.cdf)
    return res.statistic, res.pvalue

def anderson_darling(dist, x, n):
    F = np.clip(dist.cdf(x), 1e-12, 1 - 1e-12)
    i = np.arange(1, n + 1)
    return -n - np.sum((2 * i - 1) * (np.log(F) + np.log(1 - F[::-1]))) / n

def expresion_flexsim(nombre, d):
    a = d.args
    if nombre == "Normal":      return f"normal({a[0]:.4f}, {a[1]:.4f}, getstream(current))"
    if nombre == "Exponencial": return f"exponential({a[0]:.2f}, {a[1]:.4f}, getstream(current))"
    if nombre == "Gamma":       return f"gamma({a[1]:.2f}, {a[2]:.4f}, {a[0]:.4f}, getstream(current))"
    if nombre == "Erlang":      return f"erlang({a[1]:.2f}, {a[2]:.4f}, {int(a[0])}, getstream(current))"
    if nombre == "Lognormal":   return f"lognormal2({a[1]:.2f}, {a[2]:.4f}, {a[0]:.4f}, getstream(current))"
    if nombre == "Weibull":     return f"weibull({a[1]:.2f}, {a[2]:.4f}, {a[0]:.4f}, getstream(current))"
    if nombre == "Beta":        return f"beta({a[2]:.2f}, {a[2]+a[3]:.2f}, {a[0]:.4f}, {a[1]:.4f}, getstream(current))"
    if nombre == "Triangular":  return f"triangular({a[1]:.2f}, {a[1]+a[2]:.2f}, {a[1]+a[0]*a[2]:.2f}, getstream(current))"
    if nombre == "Uniforme":    return f"uniform({a[0]:.2f}, {a[0]+a[1]:.2f}, getstream(current))"
    if nombre == "Logística":   return f"logistic({a[0]:.4f}, {a[1]:.4f}, getstream(current))"

candidatas = ["Normal", "Exponencial", "Gamma", "Erlang", "Lognormal",
              "Weibull", "Beta", "Triangular", "Uniforme", "Logística"]

for VARIABLE in VARIABLES:
    print(f"\n=========================================")
    print(f"   BONDAD DE AJUSTE: {VARIABLE}")
    print(f"=========================================")
    try:
        x = np.sort(pd.read_csv(f"{CARPETA_DATOS}/{VARIABLE}.csv")["tiempo_min"].to_numpy())
    except FileNotFoundError:
        print(f"Error: No se encontró {VARIABLE}.csv")
        continue
    
    n = len(x)
    if np.ptp(x) == 0:   # EDITADO: variable constante -> se usa el valor fijo en FlexSim
        print(f"Todos los datos valen {x[0]:.4f}: variable CONSTANTE. Expresión en FlexSim: {x[0]:.4f}")
        with open(f"resultados/ajuste_{VARIABLE}.json", "w", encoding="utf-8") as f:
            json.dump({"variable": VARIABLE, "distribucion": "Constante", "parametros": f"valor={x[0]:.4f}",
                       "scipy": None, "args": [float(x[0])], "flexsim": f"{x[0]:.4f}"}, f, ensure_ascii=False, indent=2)
        continue
    if n < 30:
        print(f"¡ATENCIÓN! {VARIABLE} tiene solo {n} datos (el mínimo del curso es 30). "
              "Use el ajuste con cautela; con muy pocos datos se recomienda Triangular o Uniforme.")
    COTA_INF = 0.0
    DELTA = (x.max() - x.min()) / (n - 1)
    
    filas, modelos = [], {}
    for nombre in candidatas:
        dist, txt, n_par = ajustar(nombre, x, COTA_INF, DELTA)
        modelos[nombre] = dist
        chi2, gl, p_chi = chi_cuadrado(dist, n_par, x, n)
        ks, p_ks = kolmogorov_smirnov(dist, x)
        filas.append([nombre, txt, chi2, gl, p_chi, ks, p_ks, anderson_darling(dist, x, n)])

    tabla = pd.DataFrame(filas, columns=["Distribución", "Parámetros", "Chi²", "gl", "p Chi²", "K-S", "p K-S", "A-D"])
    tabla["Puntaje"] = tabla[["p Chi²", "p K-S"]].mean(axis=1)
    tabla["Ranking"] = 100 * tabla["Puntaje"] / tabla["Puntaje"].max()
    # EDITADO: si Chi² no tiene grados de libertad (pocos datos, p = NaN),
    # la decisión se toma solo con K-S
    acepta = ((tabla["p Chi²"] >= ALFA) | tabla["p Chi²"].isna()) & (tabla["p K-S"] >= ALFA)
    # EDITADO: un tiempo no puede ser negativo -> se descarta la distribución si P(X < 0) > 0.1 %
    negativos = tabla["Distribución"].map(lambda d: modelos[d].cdf(0) > 0.001)
    tabla["Aceptación"] = np.where(negativos, "Rechazada (valores < 0)",
                                   np.where(acepta, "No se rechaza", "Rechazada"))
    tabla = tabla.sort_values("Ranking", ascending=False).reset_index(drop=True)

    print(tabla[["Distribución", "Parámetros", "p Chi²", "p K-S", "Ranking", "Aceptación"]]
          .round({"p Chi²": 4, "p K-S": 4, "Ranking": 2}).to_string(index=False))
    tabla.to_csv(f"resultados/ranking_{VARIABLE}.csv", index=False)

    aceptadas = tabla.loc[tabla["Aceptación"] == "No se rechaza", "Distribución"].tolist()
    graficar = aceptadas[:4]
    if aceptadas:
        mejor = aceptadas[0]
    else:
        validas = tabla.loc[tabla["Aceptación"] != "Rechazada (valores < 0)", "Distribución"].tolist()
        mejor = validas[0] if validas else tabla.loc[0, "Distribución"]
        print("¡ATENCIÓN! Ninguna distribución pasó las pruebas; se toma la de mejor ranking sin valores negativos.")
        
    fila_mejor = tabla.index[tabla["Distribución"] == mejor][0]
    print("Mejor ajuste:", mejor)

    # Gráficos
    k = int(round(1 + 3.322 * np.log10(n)))
    malla = np.linspace(max(COTA_INF, x.min() - 1), x.max() + 1, 400)
    
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.hist(x, bins=k, density=True, color="#D6E6EA", edgecolor="white", label="Datos")
    for nombre, color in zip(graficar, COLORES):
        ax.plot(malla, modelos[nombre].pdf(malla), color=color, lw=2.2, label=nombre)
    ax.set_xlabel("Tiempo (min)"); ax.set_ylabel("Densidad")
    ax.set_title(f"{VARIABLE}: histograma y mejores distribuciones", loc="left", fontsize=12)
    ax.legend(frameon=False); ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout(); plt.savefig(f"figuras/03_{VARIABLE}_densidades.png", dpi=200); plt.close()

    Fn = np.arange(1, n + 1) / n
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.step(x, Fn, where="post", color="black", lw=1.5, label="Empírica (datos)")
    for nombre, color in zip(graficar, COLORES):
        ax.plot(malla, modelos[nombre].cdf(malla), color=color, lw=2, label=nombre)
    ax.set_xlabel("Tiempo (min)"); ax.set_ylabel("Probabilidad acumulada")
    ax.set_title(f"{VARIABLE}: acumulada de datos vs modelos", loc="left", fontsize=12)
    ax.legend(frameon=False); ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout(); plt.savefig(f"figuras/03_{VARIABLE}_acumuladas.png", dpi=200); plt.close()

    dist_mejor = modelos[mejor]
    p_emp = (np.arange(1, n + 1) - 0.5) / n
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.6))
    axs[0].scatter(p_emp, dist_mejor.cdf(x), s=16, color=AZUL)
    axs[0].plot([0, 1], [0, 1], color=NARANJA, lw=1.5)
    axs[0].set_title(f"Gráfico P-P ({mejor})", loc="left")
    q_teo = dist_mejor.ppf(p_emp)
    axs[1].scatter(q_teo, x, s=16, color=AZUL)
    lim = [min(q_teo.min(), x.min()), max(q_teo.max(), x.max())]
    axs[1].plot(lim, lim, color=NARANJA, lw=1.5)
    axs[1].set_title(f"Gráfico Q-Q ({mejor})", loc="left")
    for ax in axs: ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout(); plt.savefig(f"figuras/03_{VARIABLE}_pp_qq.png", dpi=200); plt.close()

    expr = expresion_flexsim(mejor, dist_mejor)
    print("Expresión en FlexSim:", expr)

    with open(f"resultados/ajuste_{VARIABLE}.json", "w", encoding="utf-8") as f:
        json.dump({"variable": VARIABLE, "distribucion": mejor, "parametros": tabla.loc[fila_mejor, "Parámetros"],
                   "scipy": dist_mejor.dist.name, "args": [float(v) for v in dist_mejor.args], "flexsim": expr},
                  f, ensure_ascii=False, indent=2)

print("\n¡Bondad de ajuste terminada para todas las variables!")

