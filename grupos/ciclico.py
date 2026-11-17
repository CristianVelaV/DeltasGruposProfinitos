"""Grupo ciclico aditivo (Z/nZ, +): enteros {0, ..., n-1} con suma
modulo n.

Presentacion: < g | g^n = 1 >, grupo ciclico de orden n.
El conjunto de generadores es configurable via build(n, generadores);
por defecto {1}, cuyo grafo de Cayley es el ciclo C_n y debe cumplir
delta(C_n) = n/4 (Gromov 1987; Bridson-Haefliger 1999, convencion
S_max <= S_med + 2δ) — es el test de calibracion del proyecto.

Nota: este modulo NO verifica que los generadores generen todo el
grupo; la conexidad del grafo de Cayley se comprueba mas adelante
en el pipeline.

PARAM = "entero": n >= 2.
"""

import math

PARAM = "entero"
PARAM_DOC = ("n >= 2: grupo ciclico aditivo Z/nZ con la suma modulo n; "
             "generadores configurables via build(n, generadores)")


def build(n, generadores=None):
    """Construye (Z/nZ, +).

    Parametros:
      n: entero >= 2, orden del grupo.
      generadores: iterable de enteros, o None (= [1] por defecto).
        Se normalizan a clases canonicas en [1, n), sin duplicados y
        ordenados (id de trabajo determinista). No se verifica que
        generen todo el grupo.

    Devuelve (elementos, identidad, mul, generadores) segun el contrato.
    Asserts: n >= 2; lista de generadores no vacia; orden == n.
    """
    n = int(n)
    assert n >= 2, "se requiere n >= 2"

    if generadores is None:
        generadores = [1]
    else:
        generadores = sorted({int(g) % n for g in generadores})
        generadores = [g for g in generadores if g != 0]

    assert generadores, "la lista de generadores no puede ser vacia"

    elementos = list(range(n))
    identidad = 0

    def mul(g, h):
        """Operacion del grupo: suma modulo n."""
        return (g + h) % n

    assert len(elementos) == n, "orden != n"
    return elementos, identidad, mul, generadores


def layout(elementos):
    """Circulo unitario con los vertices en orden 0, 1, ..., n-1."""
    k = len(elementos)
    return {a: (math.cos(2 * math.pi * a / k),
                math.sin(2 * math.pi * a / k))
            for a in elementos}