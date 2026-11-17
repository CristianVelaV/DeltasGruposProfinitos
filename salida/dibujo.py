"""salida/dibujo.py — dibujo de grafos de Cayley (única puerta a nx/mpl).

networkx/matplotlib se importan DENTRO de las funciones: importar este
módulo (o el paquete salida) no requiere tenerlas instaladas, y el
núcleo del pipeline sigue corriendo en un Python stdlib puro.

Resorte genérico: Fruchterman-Reingold (1991), vía nx.spring_layout.
"""

# Estilo visual por omisión. Para futuras opciones gráficas: agregar
# claves aquí o pasar un dict `estilo` que las pise (ver dibujar_grafo).
ESTILO_DEFECTO = {
    "figsize": (6, 6),
    "node_size": 80,
    "width": 1.0,
    "edge_color": "gray",
    "node_color": "black",
    "dpi": 120,
    "seed": 42,        # spring_layout reproducible (regla del proyecto)
}


def grafo_nx(adj):
    """Lista de adyacencia -> nx.Graph no dirigido, sin duplicados.

    Solo agrega aristas con u < v: la adyacencia es simétrica, así que
    cada arista aparece dos veces en adj y una basta.
    """
    import networkx as nx
    grafo = nx.Graph()
    grafo.add_nodes_from(range(len(adj)))
    grafo.add_edges_from(
        (u, v) for u, vecinos in enumerate(adj) for v in vecinos if u < v)
    return grafo


def resolver_posiciones(grafo, elementos, posiciones_familia, seed=42):
    """pos dict índice -> (x, y): layout de la familia o resorte.

    posiciones_familia es lo que devolvió grupos/*.py::layout(elementos):
    dict elemento -> (x, y), o None para resorte genérico. OJO con la
    traducción: layout() indexa por ELEMENTO y nx.draw por ÍNDICE.
    """
    import networkx as nx
    if posiciones_familia is None:
        return nx.spring_layout(grafo, seed=seed)
    return {i: posiciones_familia[el] for i, el in enumerate(elementos)}


def dibujar_grafo(adj, elementos=None, posiciones_familia=None, estilo=None):
    """Construye y devuelve la figura matplotlib EN MEMORIA (sin guardar).

    adj                 : lista de adyacencia (salida de nucleo.cayley).
    elementos           : lista de elementos del grupo (omiso: índices).
    posiciones_familia  : salida de layout(elementos) o None (resorte).
    estilo              : dict que pisa claves de ESTILO_DEFECTO.

    Devolver la figura en vez de una ruta la hace testeable y reusable
    (notebooks, comparaciones lado a lado) sin tocar el sistema de archivos.
    """
    import matplotlib
    matplotlib.use("Agg")            # backend sin pantalla, ANTES de pyplot
    import matplotlib.pyplot as plt
    import networkx as nx

    est = {**ESTILO_DEFECTO, **(estilo or {})}
    if elementos is None:
        elementos = list(range(len(adj)))

    grafo = grafo_nx(adj)
    pos = resolver_posiciones(grafo, elementos, posiciones_familia,
                              seed=est["seed"])

    figura, eje = plt.subplots(figsize=est["figsize"])
    nx.draw(grafo, pos, ax=eje, node_size=est["node_size"],
            width=est["width"], edge_color=est["edge_color"],
            node_color=est["node_color"])
    return figura


def guardar_png(figura, ruta, dpi=None):
    """Escribe la figura en `ruta`, la cierra y devuelve la ruta.

    Cerrar es obligatorio: en corridas largas cada figura abierta fuga
    memoria (matplotlib no las libera sola).
    """
    figura.savefig(ruta, dpi=dpi or ESTILO_DEFECTO["dpi"])
    import matplotlib.pyplot as plt
    plt.close(figura)
    return ruta
