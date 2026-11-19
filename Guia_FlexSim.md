# Guía del flujo completo 

## 0. Carpeta del proyecto

```
Proyecto/
├── datos/datos_campo.csv          <- el CSV de campo (Fecha, Hora, Franja_Horaria, Isla, Cara,
│                                      Vehiculo, Producto, Galones, Valor, Tiempo_Servicio_seg)
├── config.py                      <- VENTANA horaria, calentamiento, corrección de redondeo
├── 00_preparar_datos.py
├── 00b_franjas_horarias.py
├── 01_analisis_descriptivo.py
├── 02_pruebas_independencia.py
├── 03_bondad_ajuste.py
├── 04_validacion.py
├── 05_generar_flexsim.py
├── 06_comparar_escenarios.py
└── plantilla_modelo.fs
```

**Supuesto clave:** la columna `Hora` es la hora de **llegada** del vehículo.

**Correcciones que se declaran en la metodología:**

- La hora se anotó sin segundos, así que cada llegada se reparte uniformemente dentro de su minuto. Lo mismo se hace con el redondeo de los tiempos de servicio.
- El servicio de las motos se anotó con su valor típico (16 s) y varía entre 14 y 20 s; se modela como Triangular(14, 16, 20) s, según el criterio de la metodología del curso para datos de opinión experta.
- Los frascos de Bioacem se agrupan con las motos por su servicio corto.

---

## 1. Orden de ejecución

| Paso | Script                        | Qué hace                                                                                          | Qué produce                                                         |
| ---- | ----------------------------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 1    | `00_preparar_datos.py`      | Limpia el CSV, clasifica vehículo/producto, calcula tiempos entre llegadas y de servicio          | `datos/*.csv`, `resultados/resumen_campo.json`                   |
| 2    | `00b_franjas_horarias.py`   | Decide con pruebas K-S y Mann-Whitney qué horas se pueden agrupar en una misma franja             | `datos/entre_llegadas_F*.csv`, `resultados/franjas.json`, figura |
| 3    | `01`, `02`, `03`        | Descriptivo, independencia y bondad de ajuste de **todas** las variables (las detecta solas) | `resultados/ajuste_*.json` con la expresión FlexSim               |
| 4    | `05_generar_flexsim.py`     | Arma el script del modelo con las distribuciones reales y la preferencia de cara                   | `construir_modelo_terpel.fs`                                       |
| 5    | FlexSim                       | Construir y correr el modelo base (sección 2 y 3)                                                 | `validacion_piloto.csv`, `validacion_corridas.csv`               |
| 6    | `04_validacion.py`          | Calcula n y valida el modelo base                                                                  | Decisión de validez, figura                                         |
| 7    | FlexSim                       | Correr los escenarios 3 y 4 isleros (sección 4)                                                   | `escenario_*.csv`                                                  |
| 8    | `06_comparar_escenarios.py` | Compara escenarios contra el base                                                                  | Tabla y figura para Resultados                                       |

---

## 2. Construir el modelo en FlexSim

1. **File → New Model**: Time = **minutes**, Length = **meters**.
2. Abrir `construir_modelo_terpel.fs` con el Bloc de notas y poner `int ESCENARIO = 2;`.
3. **View → Script Console** → pegar todo → **Execute**.
4. Leer el reporte: cada línea dice **OK** o **MANUAL**.
5. Revisar en las 4 caras que *Use Operator(s) for Process* esté marcado y *Number of Operators* = 1.
6. (Opcional) Toolbox → Global Table `TablaWq` con 0 filas y 4 columnas: `Tipo`, `Producto`, `tLlegada`, `Wq_min`.
7. Guardar como `Esc_2_isleros_base.fsm`.

**Qué construye el script**

- Cola única hacia 4 caras. La Isla 1 (caras 1 y 2) la atiende `Islero_1` y la Isla 2 (caras 3 y 4) la atiende `Islero_2`.
- Cada vehículo elige cara libre según la preferencia observada en campo; por ejemplo, la cara 4 se usa más.
- Etiquetas de cada vehículo:
  - `Type`: 1 = moto, 2 = carro, 3 = camión.
  - `Producto`: 1 = gasolina, 2 = ACPM.
  - `tLlegada` y `tServ`: hora de llegada y tiempo de servicio sorteado.
- Llegadas con una distribución distinta por franja horaria.
- Servicio según el tipo de vehículo y el producto.
- Etiquetas en `Salida`:
  - `WqProm`: espera promedio en cola.
  - `VehHora`: vehículos atendidos por hora.
  - `WqGasolina` y `WqACPM`: espera según el producto.
  - `PC1` a `PC4`: % de vehículos atendidos en cada cara (validación del reparto).

**Wq se calcula como salida − llegada − servicio.** Así incluye la espera en la cara mientras el islero atiende la otra cara de su isla.

---

## 3. Verificación y corridas del modelo base

**Verificación con animación** (Reset + Run):

- [ ] `Islero_1` nunca va a las caras 3 y 4, y `Islero_2` nunca va a las caras 1 y 2.
- [ ] Los colores (tipos de vehículo) salen en proporciones parecidas a las reales.
- [ ] El reparto de vehículos por cara es parecido al real (lo imprime el script 00).
- [ ] La utilización de los isleros es menor que 100 %.

**Experimenter** (Statistics → Experimenter):

- **Run Time:** el que indica el script 05, por ejemplo 750 min. **Warmup = 0**, porque el calentamiento ya se descarta en el código.
- **Performance Measures:**
  - `WqProm`, `VehHora` y `PC1` a `PC4` de `Salida` (obligatorias).
  - `WqGasolina` y `WqACPM` (opcionales).
  - Utilización de cada islero.
- **Replications:** 20 para el piloto. Exportar el resultado a `datos/validacion_piloto.csv` con este formato:

| Observacion | wq_min | veh_hora | PC1  | PC2  | PC3  | PC4  |
| ----------- | ------ | -------- | ---- | ---- | ---- | ---- |
| 1           | 0.02   | 24.1     | 12.5 | 19.0 | 20.1 | 48.4 |

- Correr `04_validacion.py` para obtener **n**. Repetir el Experimenter con n réplicas y guardar como `datos/validacion_corridas.csv`.

---

## 4. Experimentos (escenarios)

Para cada escenario se crea un **modelo nuevo**: se cambian `ESCENARIO` y `FACTOR_DEMANDA` y se vuelve a ejecutar el script.

| ESCENARIO | FACTOR_DEMANDA | Configuración                          | Archivo de resultados              |
| --------- | -------------- | --------------------------------------- | ---------------------------------- |
| 2         | 1.0            | Base: 2 isleros fijos por isla          | `datos/escenario_base.csv`       |
| 1         | 1.0            | 1 islero para las 4 caras               | `datos/escenario_1islero.csv`    |
| 2         | 2.0            | Demanda al doble con 2 isleros          | `datos/escenario_demanda_x2.csv` |
| 1         | 2.0            | Demanda al doble con 1 islero           | `datos/escenario_1islero_x2.csv` |
| 3         | 1.0            | 2 isleros fijos + `Islero_3` de apoyo | `datos/escenario_3isleros.csv`   |
| 4         | 1.0            | 4 isleros, uno fijo por cara            | `datos/escenario_4isleros.csv`   |

- En el escenario 3, revisar que en `Despacho_Isla1` y `Despacho_Isla2` el campo *Pass To* esté en **First Available**. Así el islero de apoyo solo entra cuando el de la isla está ocupado.
- Usar el **mismo** número de réplicas y las mismas medidas en todos los escenarios. Se pueden agregar columnas como `wq_gasolina`, `wq_acpm`, `util_islero_1`; el script 06 compara todas las que encuentre.
- Los escenarios no se validan, porque no tienen datos reales; solo se compara el base contra la realidad.

---

## 5. Muestra del ciclo completo (hora pico)

1. Llenar `formato_toma_datos.csv` (separado por `;`) con las 5 marcas **con segundos** y guardarlo como `datos/datos_ciclo.csv`.
2. Ejecutar `correr_todo.py`. Detecta el archivo solo y agrega el paso `00c_preparar_ciclo.py`.
3. Construir el modelo con el nuevo `construir_modelo_terpel.fs`.
4. En el Experimenter, agregar también `WqPico` y `VehHoraPico`, y exportar las columnas `wq_pico` y `veh_hora_pico`.
5. `04_validacion.py` compara entonces el **Wq real con el simulado** en la misma ventana horaria.
