"""nucleo/cayley.py — Construcción del grafo de Cayley como lista de adyacencia.

Contrato de entrada (ver grupos/*.py):
    elementos   : iterable de elementos hasheables del grupo.
    identidad   : elemento identidad, explícito (no posicional).
    mul         : función mul(g, h) -> elemento (ley del grupo).
    generadores : iterable de generadores SIN inversos (aquí se cierran).

Salida:
    Lista de adyacencia adj donde adj[i] es la lista de índices vecinos
    del vértice i. Grafo no dirigido, sin aristas duplicadas ni lazos.
"""


def _mapa_indices(elementos):
    """Devuelve (lista_elementos, dict elemento -> índice).

    El orden de índices es el orden de `elementos`; convención del
    proyecto: el llamador pasa la identidad en la posición 0 si quiere
    que el vértice 0 sea e (usado por la optimización vértice-transitiva).
    """
    lista = list(elementos)
    idx = {g: i for i, g in enumerate(lista)}
    if len(idx) != len(lista):
        raise ValueError("elementos contiene duplicados")
    return lista, idx


def _cerrar_inversos(generadores, lista_elementos, identidad, mul):
    """Cierra el conjunto generador bajo inversos por BÚSQUEDA con mul.

    Para cada g se busca x con mul(g, x) == identidad (inverso a derecha).
    En un grupo finito el inverso a derecha coincide con el de izquierda
    y es único, así que basta encontrar uno.
    """
    cerrado = set(generadores)
    for g in generadores:
        for x in lista_elementos:
            if mul(g, x) == identidad:
                cerrado.add(x)
                break
        else:
            raise ValueError(f"generador {g!r} sin inverso: "
                             f"¿la familia construyó bien el grupo?")
    return cerrado


def cayley_adj(elementos, identidad, mul, generadores):
    """Grafo de Cayley Cay(G, S) como lista de adyacencia de índices.

    Vértices: índices 0..n-1 según el orden de `elementos`.
    Aristas: i ~ j  <=>  elementos[j] = mul(elementos[i], s) para algún
    s en el cierre de S bajo inversos (grafo no dirigido, sin duplicados).
    """
    lista, idx = _mapa_indices(elementos)
    S = _cerrar_inversos(generadores, lista, identidad, mul)

    adj = [[] for _ in range(len(lista))]
    for i, g in enumerate(lista):
        vecinos = set()          # set: colapsa duplicados si s1 != s2 dan el mismo producto
        for s in S:
            h = mul(g, s)
            if h != g:           # sin lazos (s = e no es generador, pero blindamos)
                vecinos.add(idx[h])
        adj[i] = sorted(vecinos) # orden determinista: reproducibilidad
    return adj