"""Grupo simetrico S_n ... (docstring de la Parte 4)"""

import itertools
import math

PARAM = "entero"
PARAM_DOC = "n >= 2: grupo simetrico S_n de permutaciones de n puntos"


def build(n):
    """Construye S_n: (elementos, identidad, mul, generadores)."""
    n = int(n)
    assert n >= 2, "se requiere n >= 2"

    identidad = tuple(range(n))

    def mul(f, g):
        """Composicion (f ∘ g)[i] = f[g[i]]."""
        return tuple(f[g[i]] for i in range(n))

    t = list(range(n))
    t[0], t[1] = t[1], t[0]
    transposicion = tuple(t)
    ciclo = tuple((i + 1) % n for i in range(n))
    generadores = [transposicion, ciclo]

    elementos = list(itertools.permutations(range(n)))
    assert len(elementos) == math.factorial(n), "orden != n!"
    return elementos, identidad, mul, generadores


def layout(elementos):
    """None: resorte generico."""
    return None