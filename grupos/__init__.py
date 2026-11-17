"""Registro de familias de grupos disponibles para el pipeline.

Cada familia es un módulo dentro de este paquete que expone el contrato:
PARAM, PARAM_DOC, build(param), layout(elementos).
"""

from . import dihedral, ciclico, psl2, symmetric, unidades

FAMILIAS = {
    "dihedral": dihedral,
    "ciclico": ciclico,
    "psl2": psl2,
    "symmetric": symmetric,
    "unidades": unidades,
}

__all__ = ["FAMILIAS"]