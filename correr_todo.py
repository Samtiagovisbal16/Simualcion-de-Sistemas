# -*- coding: utf-8 -*-
"""
Corre en orden 00 -> 00b -> 01 -> 02 -> 03 -> 05 y guarda TODA la salida en
resultados/salida_consola.txt (ese es el archivo que se envía para revisión).
Se detiene si un script falla.
"""
import os
import sys
import subprocess

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    pass
os.makedirs("resultados", exist_ok=True)

SCRIPTS = ["00_preparar_datos.py", "00b_franjas_horarias.py"]
if os.path.exists("datos/datos_ciclo.csv"):          # muestra del ciclo completo (hora pico)
    SCRIPTS.append("00c_preparar_ciclo.py")
if os.path.exists("datos/muestra_pico.csv"):          # muestra de hora pico (multitarea)
    SCRIPTS.append("00d_muestra_pico.py")
SCRIPTS += ["01_analisis_descriptivo.py",
           "02_pruebas_independencia.py", "03_bondad_ajuste.py", "05_generar_flexsim.py"]

entorno = dict(os.environ, MPLBACKEND="Agg", PYTHONIOENCODING="utf-8")
with open("resultados/salida_consola.txt", "w", encoding="utf-8") as log:
    for s in SCRIPTS:
        print(f"Ejecutando {s} ...", end=" ", flush=True)
        r = subprocess.run([sys.executable, s], capture_output=True, text=True, encoding="utf-8", env=entorno)
        log.write(f"\n{'#' * 70}\n# {s}\n{'#' * 70}\n{r.stdout}{r.stderr}")
        if r.returncode != 0:
            print("ERROR")
            print(r.stderr[-2000:])
            print("\nSe detuvo. Envíe resultados/salida_consola.txt")
            break
        print("OK")
    else:
        print("\nTodo terminó bien.")
        print("Envíe: resultados/salida_consola.txt, figuras/00b_franjas_horarias.png y construir_modelo.fs")
