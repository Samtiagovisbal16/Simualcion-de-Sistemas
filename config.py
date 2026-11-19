# -*- coding: utf-8 -*-
"""
CONFIGURACIÓN COMÚN DEL PROYECTO
La leen 00, 00b, 04 y 05. Cambie aquí y vuelva a correr desde 00.
"""
VENTANA = (6, 21)          # horas simuladas y validadas: 06:00 a 21:00 (turno de día, 2 isleros)
WARMUP = 30                # min de calentamiento antes de la ventana (no se cuentan)
CORREGIR_REDONDEO = True   # reparte cada registro redondeado dentro de su intervalo de medición
SEMILLA = 2026             # semilla de la corrección (resultados reproducibles)
MIN_DATOS_FRANJA = 30      # una franja con menos datos se une a la vecina más parecida

# Tiempos de servicio que NO se cronometraron uno a uno, sino que se anotaron con su
# valor típico. Se modelan con una distribución triangular (mín, más probable, máx) en SEGUNDOS,
# como indica la metodología del curso cuando hay pocos datos u opinión experta.
SERVICIO_EXPERTO = {
    "moto": (14, 16, 20),   # motos y compras en recipiente: entre 14 y 20 s, típico 16 s
}

# Variables que se modelan con su DISTRIBUCIÓN EMPÍRICA (los propios datos, interpolados),
# porque ninguna distribución teórica pasó las pruebas (Law y Kelton recomiendan esta
# alternativa). Se pueden agregar franjas de llegada, por ejemplo "entre_llegadas_F1_06a09".
USAR_EMPIRICA = ["servicio_carro", "servicio_camion"]

# Mínimo de vehículos de un tipo en la muestra del ciclo completo para usar su servicio total
# directamente; con menos, se usa el flujo de los registros anteriores + la atención sin flujo.
MIN_DATOS_SERVICIO = 30

# Tiempo de PREPARACIÓN que no se midió en la muestra de hora pico: la moto entra, se ubica,
# el islero abre el tanque y pregunta cuánto (ocurre antes de que el surtidor empiece a marcar).
# Si lo miden (o lo estiman), escríbanlo aquí como (mínimo, más probable, máximo) en segundos.
# None = no se agrega (el servicio queda subestimado, como se discute en el informe).
PREPARACION_S = None

# Muestra de hora pico: usar en esa ventana la tasa de llegada medida en campo (ráfaga de motos)
USAR_LLEGADAS_PICO_CAMPO = True
# Si PREPARACION_S es None, usar la preparación de moto estimada a partir de la ráfaga
USAR_PREPARACION_ESTIMADA = True
