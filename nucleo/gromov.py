"""Núcleo métrico: BFS y constante de hiperbolicidad δ de Gromov.

Referencias:
- BFS: Cormen, Leiserson, Rivest & Stein, "Introduction to Algorithms",
  3ª ed., §22.2.
- Condición de cuatro puntos: Gromov (1987), "Hyperbolic groups", en
  Essays in Group Theory (ed. Gersten); Bridson & Haefliger (1999),
  "Metric Spaces of Non-Positive Curvature", §III.H.1, Def. 1.16.
  Convención: S_max <= S_med + 2δ, es decir δ = max (S_max − S_med)/2.

Solo stdlib. Nada de networkx aquí (regla del proyecto).
"""
from collections import deque
from itertools import combinations


class GrafoDisconexoError(ValueError):
    """Cay(G, S) es disconexo: el conjunto generador S no genera el grupo.

    Hereda de ValueError (es un error de ENTRADA, no de cómputo) pero con
    nombre propio para que worker.py capture exactamente este caso.
    """

def matriz_distancias(adj):
    """Distancias mínimas entre todo par de vértices (BFS por origen).

    adj: lista de adyacencia, adj[u] = iterable de vecinos de u.
    Devuelve matriz n×n de enteros; dist[u][v] = d(u, v).
    -1 residual indicaría vértice inalcanzable (grafo disconexo).
    Complejidad: O(n·(n+m)) tiempo, O(n²) memoria.
    """
    n = len(adj)
    dist = [[-1] * n for _ in range(n)]  # -1 = no visitado
    for origen in range(n):
        d = dist[origen]          # alias a la fila: escribe en dist[origen]
        d[origen] = 0
        cola = deque([origen])    # popleft() O(1); FIFO = BFS (CLRS §22.2)
        while cola:
            u = cola.popleft()
            du = d[u] + 1         # d[u] ya es definitiva al extraer u
            for v in adj[u]:
                if d[v] == -1:
                    d[v] = du     # marcar AL ENCOLAR, no al extraer
                    cola.append(v)
    return dist


def gromov_delta_y_diametro(adj):
    """(delta, diametro) del grafo, convención S_max ≤ S_med + 2δ.

    Un punto de cada cuádrupla se fija en el vértice 0: válido en grafos
    vértice-transitivos (los de Cayley), O(n³) en vez de O(n⁴).
    δ se acumula duplicado (entero 2δ) y se divide solo al final:
    sin errores de coma flotante; el resultado es semientero exacto.
    """
    dist = matriz_distancias(adj)
    n = len(adj)

    # Conectividad: en un grafo no dirigido basta revisar la fila del
    # vértice 0; si todo es alcanzable desde él, el grafo es conexo.
    # Si no, S no genera el grupo y cualquier (delta, diametro) sería falso.

    inalcanzables = [v for v in range(n) if dist[0][v] == -1]
    
    if inalcanzables:
        raise GrafoDisconexoError(
            f"Cay(G, S) disconexo: {len(inalcanzables)} de {n} vértices "
            f"inalcanzables desde la identidad (p. ej. índices "
            f"{inalcanzables[:5]}). El conjunto generador S no genera "
            f"el grupo.")

    d0 = dist[0]
    delta_doble = 0
    for b, c, e in combinations(range(1, n), 3):
        db, dc, de = d0[b], d0[c], d0[e]
        s0 = db + dist[c][e]      # emparejamiento (0,b)(c,e)
        s1 = dc + dist[b][e]      # emparejamiento (0,c)(b,e)
        s2 = de + dist[b][c]      # emparejamiento (0,e)(b,c)
        smax = max(s0, s1, s2)
        smin = min(s0, s1, s2)
        smed = s0 + s1 + s2 - smax - smin  # mediana de 3 sin ordenar
        if smax - smed > delta_doble:
            delta_doble = smax - smed
    diametro = max(max(fila) for fila in dist)
    return delta_doble / 2, diametro