"""Calibración del núcleo métrico. Ejecutar: python -m nucleo.calibracion

Verifica los valores de referencia:
- Ciclos C_n. OJO: δ(C_n) = n/4 solo cuando 4 | n. Los valores usados aquí
  (C4=1, C5=0.5, C6=1, C8=2, C12=3) fueron verificados por fuerza bruta
  O(n⁴) sin punto fijo, y coinciden con el cálculo con punto fijo (lo que
  además valida la optimización de vértice-transitividad).
- Árbol binario completo de 7 nodos: δ = 0 (los árboles son 0-hiperbólicos;
  Gromov 1987).

Imprime PASS/FAIL por test y lanza AssertionError si alguno falla.
"""
from nucleo.gromov import gromov_delta_y_diametro, GrafoDisconexoError


def ciclo(n):
    """Lista de adyacencia del ciclo C_n = Cay(ℤ/nℤ, {±1})."""
    return [[(i - 1) % n, (i + 1) % n] for i in range(n)]


def arbol_binario_7():
    """Árbol binario completo de 7 nodos (raíz 0, hijos 2i+1 y 2i+2)."""
    adj = [[] for _ in range(7)]
    for i in range(1, 7):
        padre = (i - 1) // 2       # indexación tipo heap (Williams 1964)
        adj[padre].append(i)       # arista en ambos sentidos: no dirigido
        adj[i].append(padre)
    return adj


def _check(nombre, adj, delta_esperado):
    """Ejecuta el núcleo sobre adj y compara con el valor de referencia."""
    delta, diametro = gromov_delta_y_diametro(adj)
    ok = delta == delta_esperado   # == seguro: ambos son múltiplos de 0.5
    print(f"{'PASS' if ok else 'FAIL'}  {nombre}: delta={delta} "
          f"(esperado {delta_esperado}), diametro={diametro}")
    return ok


def dos_triangulos():
    """Dos C_3 disjuntos: grafo disconexo (equivale a S que no genera)."""
    return [[1, 2], [0, 2], [0, 1], [4, 5], [3, 5], [3, 4]]


def _check_disconexo():
    """El núcleo debe RECHAZAR un grafo disconexo, no dar un δ falso."""
    try:
        gromov_delta_y_diametro(dos_triangulos())
        print("FAIL  disconexo: no lanzó GrafoDisconexoError")
        return False
    except GrafoDisconexoError as e:
        print(f"PASS  disconexo: GrafoDisconexoError lanzado ({e})")
        return True


def main():
    tests = [
        ("C4", ciclo(4), 1.0),
        ("C5", ciclo(5), 0.5),
        ("C6", ciclo(6), 1.0),
        ("C8", ciclo(8), 2.0),
        ("C12", ciclo(12), 3.0),
        ("arbol_binario_7", arbol_binario_7(), 0.0),
    ]
    # Lista (no generador): ejecuta TODOS los tests antes del assert.
    resultados = [_check(nombre, adj, esp) for nombre, adj, esp in tests]
    resultados.append(_check_disconexo())
    assert all(resultados), "Calibración FALLIDA: revisar nucleo/gromov.py"
    print("Todos los tests PASS.")


if __name__ == "__main__":
    main()