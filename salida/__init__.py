"""salida/ — capa de presentación del pipeline.

ÚNICO paquete del proyecto que toca networkx/matplotlib, y solo para
dibujar: la regla "stdlib puro en el núcleo" se audita con
`grep -r networkx nucleo/ grupos/ worker.py` → cero imports.
"""

from .dibujo import ESTILO_DEFECTO, dibujar_grafo, guardar_png

__all__ = ["ESTILO_DEFECTO", "dibujar_grafo", "guardar_png"]
