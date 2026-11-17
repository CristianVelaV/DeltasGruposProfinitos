"""Familia de grupos dihedrales D_n = <r, s | r^n = s^2 = 1, s·r·s = r^-1>.

Convención de elementos: (a, k) representa r^k · s^a con
a en {0, 1} (exponente de s) y k en Z/n (exponente de r).
"""

import math

PARAM = "entero"
PARAM_DOC = "n: rotaciones; el grupo tiene orden 2n"


def _mul(n):
    """Devuelve la operación de grupo de D_n como closure sobre n."""
    def mul(p, q):
        """Multiplica p=(a,k), q=(b,j): r^k·s^a · r^j·s^b.

        Si a == 0: r^k·r^j·s^b        -> (a+b mod 2, (k+j) mod n)
        Si a == 1: r^k·(r^-j·s)·s^b  -> (a+b mod 2, (k-j) mod n)
        usando s·r = r^-1·s (equivalente a la relación srs = r^-1).
        """
        a, k = p
        b, j = q
        if a == 0:
            return ((a + b) % 2, (k + j) % n)
        return ((a + b) % 2, (k - j) % n)
    return mul


def build(n):
    """Construye D_n; devuelve (elementos, identidad, mul, generadores).

    Incluye asserts de la presentación: relaciones y orden esperado.
    """
    if not isinstance(n, int) or n < 1:
        raise ValueError(f"n debe ser un entero >= 1, recibido: {n!r}")

    elementos = [(a, k) for a in (0, 1) for k in range(n)]
    identidad = (0, 0)
    mul = _mul(n)
    generadores = [(0, 1), (1, 0)]  # r y s, SIN inversos (el núcleo cierra)

    # --- Asserts de la presentación ---
    r, s = generadores
    assert len(elementos) == 2 * n, "orden incorrecto"
    assert mul(s, s) == identidad, "s^2 != 1"
    assert mul(r, (0, n - 1)) == identidad, "r·r^(n-1) != 1 (r^n != 1)"
    assert mul(s, mul(r, s)) == (0, n - 1), "srs != r^-1"
    assert len(set(elementos)) == 2 * n, "elementos duplicados"

    return elementos, identidad, mul, generadores


def layout(elementos):
    """Posiciones canónicas: rotaciones en círculo exterior, reflexiones en
    círculo interior concéntrico, ambos en orden angular creciente de k.
    """
    n = len(elementos) // 2  # orden del grupo = 2n  =>  n = |elementos|/2
    exterior, interior = 1.0, 0.5  # [APROXIMACIÓN/ESPECULACIÓN]: radios
    pos = {}
    for (a, k) in elementos:
        angulo = 2.0 * math.pi * k / n
        radio = exterior if a == 0 else interior
        pos[(a, k)] = (radio * math.cos(angulo), radio * math.sin(angulo))
    return pos