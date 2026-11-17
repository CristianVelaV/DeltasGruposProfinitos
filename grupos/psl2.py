"""PSL(2, p) = SL(2, p)/{+-I} ... (docstring de la Parte 3)"""

PARAM = "primo"
PARAM_DOC = "p primo: grupo proyectivo especial lineal PSL(2, p)"


def _es_primo(p):
    """Primalidad por division tentativa hasta sqrt(p)."""
    if p < 2:
        return False
    if p % 2 == 0:
        return p == 2
    r = 3
    while r * r <= p:
        if p % r == 0:
            return False
        r += 2
    return True


def _mul_sl2(A, B, p):
    """Producto de matrices 2x2 (tuplas fila) modulo p, sin canonizar."""
    a, b, c, d = A
    e, f, g, h = B
    return ((a * e + b * g) % p, (a * f + b * h) % p,
            (c * e + d * g) % p, (c * f + d * h) % p)


def _canon(A, p):
    """Representante canonico de {A, -A}: min lexicografico."""
    return min(A, tuple((-x) % p for x in A))


def build(p):
    """Construye PSL(2,p) por clausura BFS desde la identidad."""
    p = int(p)
    assert _es_primo(p), "se requiere p primo"

    identidad = _canon((1 % p, 0, 0, 1 % p), p)

    def mul(A, B):
        """Producto en PSL: multiplicar en SL y canonizar."""
        return _canon(_mul_sl2(A, B, p), p)

    def inv(A):
        """Inversa SL(2): (d, -b, -c, a), canonizada."""
        a, b, c, d = A
        return _canon((d, (-b) % p, (-c) % p, a), p)

    S = _canon((1 % p, 1 % p, 0, 1 % p), p)
    T = _canon((1 % p, 0, 1 % p, 1 % p), p)
    generadores = [S, T]

    # Clausura BFS (Cormen et al., Introduction to Algorithms, sec. 22.2)
    vistos = {identidad}
    cola = [identidad]
    i = 0
    while i < len(cola):
        A = cola[i]
        i += 1
        for G in generadores:
            for B in (mul(A, G), mul(A, inv(G))):
                if B not in vistos:
                    vistos.add(B)
                    cola.append(B)

    elementos = sorted(vistos)
    esperado = 6 if p == 2 else p * (p * p - 1) // 2
    assert len(elementos) == esperado, "orden de PSL(2,p) incorrecto"
    return elementos, identidad, mul, generadores


def layout(elementos):
    """None: resorte generico."""
    return None