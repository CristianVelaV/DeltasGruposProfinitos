"""Grupo de unidades (Z/nZ)x ... (docstring de la Parte 2)"""

import math

PARAM = "entero"
PARAM_DOC = "n >= 2: grupo multiplicativo (Z/nZ)x de unidades modulo n"


def _euler_phi(n):
    """phi(n) contando coprimos en [1, n] (definicion de Euler)."""
    return sum(1 for a in range(1, n + 1) if math.gcd(a, n) == 1)


def build(n):
    """Construye (Z/nZ)x: (elementos, identidad, mul, generadores)."""
    n = int(n)
    assert n >= 2, "se requiere n >= 2"

    elementos = [a for a in range(1, n) if math.gcd(a, n) == 1]
    identidad = 1

    def mul(a, b):
        """Multiplicacion modular."""
        return (a * b) % n

    generadores = [g for g in (2, 3)
                   if g < n and math.gcd(g, n) == 1 and g != 1]

    # [APROXIMACION] fallback heuristico: menor unidad != 1.
    if not generadores:
        candidatos = [a for a in elementos if a != identidad]
        generadores = candidatos[:1]

    assert len(elementos) == _euler_phi(n), "orden != phi(n)"
    return elementos, identidad, mul, generadores


def layout(elementos):
    """Circulo unitario ordenado por valor; dict elemento -> (x, y)."""
    k = len(elementos)
    return {a: (math.cos(2 * math.pi * i / k),
                math.sin(2 * math.pi * i / k))
            for i, a in enumerate(sorted(elementos))}