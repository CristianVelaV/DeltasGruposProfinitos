"""worker.py — CLI del pipeline de δ de Gromov.

Subcomandos:
    nuevo   FAMILIA --gens G1,G2 (--p COTA|--p LISTA|--n LISTA/RANGO) [--e K|A-B]
            [--img extremos|todos|LISTA/RANGO]   (sin --img: no se dibuja nada)
    correr  CARPETA
    estado  CARPETA

Cada corrida vive en calculos_delta/<nombre>/ (el nombre resume el comando).

Solo stdlib en el núcleo. SQLite (WAL) es la única fuente de verdad;
resultados.csv y resumen.txt son vistas derivadas que se regeneran completas
al terminar o al interrumpir. networkx/matplotlib se importan SOLO desde el
paquete salida/ (capa de presentación, nunca en el cómputo).
"""

import argparse
import csv
import hashlib
import importlib
import os
import re
import sqlite3
import sys
import time
from datetime import datetime

import primos
from grupos import FAMILIAS
from nucleo.cayley import cayley_adj
from nucleo.gromov import gromov_delta_y_diametro, GrafoDisconexoError

ESQUEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS meta (
    clave TEXT PRIMARY KEY,
    valor TEXT
);

CREATE TABLE IF NOT EXISTS trabajos (
    id         TEXT PRIMARY KEY,
    param      INTEGER NOT NULL,
    estado     TEXT NOT NULL DEFAULT 'pendiente'
               CHECK (estado IN ('pendiente', 'en_curso', 'hecho', 'fallido')),
    con_imagen INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS resultados (
    trabajo_id TEXT PRIMARY KEY REFERENCES trabajos(id),
    orden      INTEGER NOT NULL,
    delta      REAL    NOT NULL,
    diametro   INTEGER NOT NULL,
    segundos   REAL
);
"""


def crear_bd(ruta_db, familia, gens, comando):
    """Crea deltas.db con el esquema y la tabla meta; devuelve la conexión."""
    con = sqlite3.connect(ruta_db)
    con.executescript(ESQUEMA)
    con.execute("INSERT OR REPLACE INTO meta VALUES ('familia', ?)", (familia,))
    con.execute("INSERT OR REPLACE INTO meta VALUES ('gens', ?)", (",".join(gens),))
    con.execute("INSERT OR REPLACE INTO meta VALUES ('comando', ?)", (comando,))
    con.commit()
    return con


def expandir_lista_o_rango(texto):
    """'3,5,7' -> [3,5,7]; '3-9' -> [3,4,5,6,7,8,9]. Rango inclusivo."""
    if "-" in texto:
        a, b = texto.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(t) for t in texto.split(",")]


def fabricar_parametros(args):
    """Resuelve (--p | --n) y --e a la lista de parámetros enteros a encolar."""
    if args.p is not None:
        if args.p.isdigit():                    # --p COTA
            base = [p for p in primos.PRIMOS if p <= int(args.p)]
        else:                                   # --p lista
            pedidos = [int(t) for t in args.p.split(",")]
            base = [p for p in pedidos if p in primos.PRIMOS]
            if len(base) != len(pedidos):
                faltan = set(pedidos) - set(base)
                raise ValueError(f"{sorted(faltan)} no están en primos.PRIMOS")
    else:                                       # --n lista/rango
        base = expandir_lista_o_rango(args.n)

    if args.e is None:                          # omiso = exponente 1
        return base
    exponentes = expandir_lista_o_rango(args.e)
    return [p ** e for p in base for e in exponentes]


def validar_param(familia_mod, param):
    """Verifica param contra el PARAM declarado por la familia. Lanza ValueError."""
    tipo = familia_mod.PARAM
    if tipo == "entero":
        if param < 1:
            raise ValueError(f"{param}: PARAM='entero' exige param >= 1")
    elif tipo == "primo":
        if param not in primos.PRIMOS:
            raise ValueError(f"{param} no es primo (no está en primos.PRIMOS)")
    elif tipo == "potencia de primo":
        es = any(param == p ** e
                 for p in primos.PRIMOS
                 for e in range(1, 10) if p ** e <= param)
        if not es:
            raise ValueError(f"{param} no es potencia de primo")
    else:
        raise ValueError(f"PARAM desconocido: {tipo!r}")


def params_con_imagen(opcion_img, params):
    """Resuelve --img a los parámetros marcados con con_imagen = 1.

    None (sin --img) -> ninguno; 'extremos' -> {min, max}; 'todos' -> todos;
    si no, lista/rango ('3,5' | '3-8').
    Lanza ValueError si se pide un parámetro que no está en la corrida.
    """
    if opcion_img is None:
        return set()
    if opcion_img == "todos":
        return set(params)
    if opcion_img == "extremos":
        return {min(params), max(params)}
    pedidos = set(expandir_lista_o_rango(opcion_img))
    desconocidos = pedidos - set(params)
    if desconocidos:
        raise ValueError(f"--img pide {sorted(desconocidos)} "
                         f"que no están en la corrida {params}")
    return pedidos


def trabajo_id(familia, param, gens):
    """Id determinista: sha1 de 'familia|param|gens' (gens en orden dado)."""
    huella = f"{familia}|{param}|{','.join(gens)}"
    return hashlib.sha1(huella.encode("utf-8")).hexdigest()


CARPETA_BASE = "calculos_delta"


def _segmento(texto):
    """Valor de la línea de comandos -> trozo seguro para un nombre de carpeta.

    ',' pasa a '+' (los rangos conservan su '-') y cualquier otro carácter
    que no sea letra, dígito, '+' o '-' pasa a '_'.
    """
    return re.sub(r"[^A-Za-z0-9+\-]", "_", texto.replace(",", "+"))


def nombre_corrida(args, gens, params, fecha):
    """Nombre de carpeta que resume el comando, con la fecha al final.

    <familia>_gens<G>_<p|pmax|n><valores>[_e<exp>]_<fecha>
    Ejemplos: ciclico_gens2+3_n2_e1-9_20261114_214030
              ciclico_gens1_pmax13_20261114_214030   (--p 13 es una cota)
    Si el nombre sin fecha pasa de 60 caracteres, los parámetros se abrevian
    a params<min>-<max>x<cantidad> (valores finales, ya con el exponente).
    Si la lista de generadores pasa de 40 caracteres, se dejan los tres
    primeros seguidos de etc<cantidad>. El comando completo queda en
    resumen.txt.
    """
    gens_seg = "gens" + _segmento(",".join(gens))
    if len(gens_seg) > 40:
        gens_seg = f"gens{_segmento(','.join(gens[:3]))}etc{len(gens)}"
    if args.p is not None:
        base = ("p" if "," in args.p else "pmax") + _segmento(args.p)
    else:
        base = "n" + _segmento(args.n)
    expo = f"_e{_segmento(args.e)}" if args.e else ""
    nombre = f"{args.familia}_{gens_seg}_{base}{expo}"
    if len(nombre) > 60:
        nombre = (f"{args.familia}_{gens_seg}_"
                  f"params{min(params)}-{max(params)}x{len(params)}")
    return f"{nombre}_{fecha}"


def cmd_nuevo(args):
    """Crea la carpeta de corrida, la BD y encola todos los trabajos."""
    if args.familia not in FAMILIAS:
        sys.exit(f"error: familia desconocida {args.familia!r}. "
                 f"Disponibles: {sorted(FAMILIAS)}")
    familia_mod = importlib.import_module(f"grupos.{args.familia}")
    gens = args.gens.split(",")

    try:
        params = fabricar_parametros(args)
    except ValueError as e:
        sys.exit(f"error en parámetros: {e}")
    for p in params:                        # validación ANTES de encolar nada
        try:
            validar_param(familia_mod, p)
        except ValueError as e:
            sys.exit(f"error: {e}")
    try:                                    # --img también se valida antes de crear nada
        marcados = params_con_imagen(args.img, params)
    except ValueError as e:
        sys.exit(f"error en --img: {e}")

    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    carpeta = os.path.join(CARPETA_BASE,
                           nombre_corrida(args, gens, params, fecha))
    os.makedirs(carpeta, exist_ok=True)
    if marcados:                            # img/ solo si hay algo que dibujar
        os.makedirs(os.path.join(carpeta, "img"), exist_ok=True)

    comando = "python worker.py " + " ".join(sys.argv[1:])

    con = crear_bd(os.path.join(carpeta, "deltas.db"), args.familia, gens, comando)
    with con:                               # UNA transacción para toda la cola
        for p in params:
            con.execute(
                "INSERT OR IGNORE INTO trabajos (id, param, estado, con_imagen) "
                "VALUES (?, ?, 'pendiente', ?)",
                (trabajo_id(args.familia, p, gens), p, int(p in marcados)))
    con.close()
    regenerar_resumen(carpeta, familia_mod, args.familia, gens)
    print(f"[nuevo] {len(params)} trabajos encolados en {carpeta} "
          f"({len(marcados)} con imagen)")


def abrir_corrida(carpeta):
    """Abre deltas.db de una corrida y recupera (familia, gens) de meta.

    Migra corridas creadas antes del estado 'fallido': si el CHECK de
    trabajos.estado no lo incluye, reconstruye la tabla conservando filas
    (SQLite no permite ALTER del CHECK; tabla nueva + INSERT SELECT).
    """
    ruta_db = os.path.join(carpeta, "deltas.db")
    if not os.path.isfile(ruta_db):
        sys.exit(f"error: no existe {ruta_db}")
    con = sqlite3.connect(ruta_db)
    ddl = con.execute(
        "SELECT sql FROM sqlite_master WHERE name='trabajos'").fetchone()[0]
    if "'fallido'" not in ddl:
        with con:
            con.execute("ALTER TABLE trabajos RENAME TO trabajos_vieja")
            con.execute(
                "CREATE TABLE trabajos ("
                " id TEXT PRIMARY KEY,"
                " param INTEGER NOT NULL,"
                " estado TEXT NOT NULL DEFAULT 'pendiente'"
                " CHECK (estado IN ('pendiente','en_curso','hecho','fallido')),"
                " con_imagen INTEGER NOT NULL DEFAULT 0)")
            con.execute("INSERT INTO trabajos SELECT * FROM trabajos_vieja")
            con.execute("DROP TABLE trabajos_vieja")
    columnas = [c[1] for c in con.execute("PRAGMA table_info(resultados)")]
    if "segundos" not in columnas:          # corridas anteriores al tiempo
        with con:
            con.execute("ALTER TABLE resultados ADD COLUMN segundos REAL")
    meta = dict(con.execute("SELECT clave, valor FROM meta"))
    return con, meta["familia"], meta["gens"].split(",")


def regenerar_csv(carpeta):
    """Reescribe resultados.csv COMPLETO desde SQLite (solo trabajos 'hecho').

    El CSV es una vista derivada: se borra y se reescribe entero, nunca se
    anexa durante el cómputo. Devuelve el número de filas escritas.
    """
    con = sqlite3.connect(os.path.join(carpeta, "deltas.db"))
    filas = con.execute(
        "SELECT r.orden, r.delta, r.diametro "
        "FROM resultados r JOIN trabajos t ON t.id = r.trabajo_id "
        "WHERE t.estado = 'hecho' ORDER BY t.param").fetchall()
    con.close()
    ruta = os.path.join(carpeta, "resultados.csv")
    with open(ruta, "w", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(["orden", "delta", "diametro"])
        escritor.writerows(filas)
    return len(filas)


def regenerar_resumen(carpeta, familia_mod, familia, gens):
    """Reescribe resumen.txt COMPLETO desde SQLite.

    Vista derivada, como resultados.csv: arranca con el comando que creó
    la corrida y sigue con una ficha por trabajo 'hecho' o 'fallido', en
    orden de parámetro. El tiempo cubre solo gromov_delta_y_diametro.
    """
    con = sqlite3.connect(os.path.join(carpeta, "deltas.db"))
    comando = con.execute(
        "SELECT valor FROM meta WHERE clave='comando'").fetchone()[0]
    filas = con.execute(
        "SELECT t.param, t.estado, r.orden, r.delta, r.diametro, r.segundos "
        "FROM trabajos t LEFT JOIN resultados r ON r.trabajo_id = t.id "
        "WHERE t.estado IN ('hecho', 'fallido') ORDER BY t.param").fetchall()
    con.close()
    with open(os.path.join(carpeta, "resumen.txt"), "w") as f:
        f.write(f"comando: {comando}\n")
        for param, estado, orden, delta, diametro, segundos in filas:
            f.write(f"\ngrupo:       {familia}({param})\n")
            if estado == "fallido":
                f.write("fallo:       los generadores no generan el grupo\n")
                continue
            tiempo = ("no registrado" if segundos is None
                      else f"{segundos:.3f} s")
            f.write(f"descripcion: {familia_mod.PARAM_DOC}\n")
            f.write(f"parametro:   {param} ({familia_mod.PARAM})\n")
            f.write(f"generadores: {', '.join(gens)} "
                    f"(cerrados bajo inversos en el nucleo)\n")
            f.write(f"orden:       {orden}\n")
            f.write(f"delta:       {delta}\n")
            f.write(f"diametro:    {diametro}\n")
            f.write(f"tiempo:      {tiempo}\n")


def dibujar_png(carpeta, tag, familia_mod, elementos, adj):
    """Dibuja el grafo de Cayley en img/<tag>.png y devuelve la ruta.

    Intermediario delgado: el worker decide DÓNDE va el archivo; el
    paquete salida decide CÓMO se dibuja. El import es perezoso para
    que `worker.py` arranque en un Python sin networkx/matplotlib.
    """
    from salida.dibujo import dibujar_grafo, guardar_png

    figura = dibujar_grafo(adj, elementos=elementos,
                           posiciones_familia=familia_mod.layout(elementos))
    ruta = os.path.join(carpeta, "img", tag + ".png")
    return guardar_png(figura, ruta)


def cmd_correr(args):
    """Procesa la cola: reanuda huérfanos, ejecuta pendientes, Ctrl-C limpio.

    Tras cada trabajo confirmado en SQLite escribe su PNG (si con_imagen=1).
    Al terminar o al interrumpir, regenera resultados.csv y resumen.txt.
    """
    con, familia, gens = abrir_corrida(args.carpeta)
    familia_mod = importlib.import_module(f"grupos.{familia}")

    with con:   # trabajos interrumpidos en una corrida anterior vuelven a la cola
        con.execute("UPDATE trabajos SET estado='pendiente' "
                    "WHERE estado='en_curso'")

    pendientes = con.execute(
        "SELECT id, param, con_imagen FROM trabajos WHERE estado='pendiente' "
        "ORDER BY param").fetchall()
    total = con.execute("SELECT COUNT(*) FROM trabajos").fetchone()[0]
    hechos = total - len(pendientes)

    try:
        for i, (tid, param, con_img) in enumerate(pendientes, 1):
            con.execute("UPDATE trabajos SET estado='en_curso' WHERE id=?",
                        (tid,))
            con.commit()                    # marca visible antes de calcular

            try:
                elementos, identidad, mul, generadores = familia_mod.build(
                    param, [int(g) for g in gens])
                adj = cayley_adj(elementos, identidad, mul, generadores)
                t0 = time.perf_counter()
                delta, diametro = gromov_delta_y_diametro(adj)
                segundos = time.perf_counter() - t0
            except GrafoDisconexoError as e:
                # S no genera el grupo: avisar y SEGUIR con la cola
                # (resumen.txt lo registra al regenerarse). No se escribe
                # nada en `resultados`, así que ningún valor falso llega
                # a resultados.csv.
                print(f"[correr {i}/{len(pendientes)}] {familia}({param}): "
                      f"FALLIDO — {e}")
                with con:               # estado propio: no se reintentará
                    con.execute("UPDATE trabajos SET estado='fallido' "
                                "WHERE id=?", (tid,))
                continue

            with con:                       # resultado + estado en UNA transacción
                con.execute(
                    "INSERT OR REPLACE INTO resultados "
                    "(trabajo_id, orden, delta, diametro, segundos) "
                    "VALUES (?,?,?,?,?)",
                    (tid, len(elementos), delta, diametro, segundos))
                con.execute("UPDATE trabajos SET estado='hecho' WHERE id=?",
                            (tid,))

            # Vistas derivadas: SOLO después de confirmar en la fuente de verdad
            if con_img:
                tag = f"{familia}_{param}"
                dibujar_png(args.carpeta, tag, familia_mod, elementos, adj)

            hechos += 1
            print(f"[correr {i}/{len(pendientes)}] {familia}({param}): "
                  f"orden={len(elementos)} delta={delta} "
                  f"diametro={diametro}  ({hechos}/{total} hechos)")
    except KeyboardInterrupt:
        print("\n[correr] interrumpido; el trabajo en_curso quedará "
              "marcado y volverá a 'pendiente' al reanudar.")
    finally:
        con.close()
        filas = regenerar_csv(args.carpeta)  # tanto fin normal como Ctrl-C
        regenerar_resumen(args.carpeta, familia_mod, familia, gens)
        print(f"[correr] resultados.csv regenerado ({filas} filas).")
        print("[correr] resumen.txt regenerado.")
    print(f"[correr] fin: {hechos}/{total} trabajos hechos.")


def cmd_estado(args):
    """Imprime hechos/total de una corrida."""
    con, familia, gens = abrir_corrida(args.carpeta)
    filas = con.execute(
        "SELECT estado, COUNT(*) FROM trabajos GROUP BY estado").fetchall()
    conteo = dict(filas)
    total = sum(conteo.values())
    hechos = conteo.get("hecho", 0)
    print(f"{args.carpeta} [{familia}, gens={','.join(gens)}]: "
          f"{hechos}/{total} hechos "
          f"(pendiente={conteo.get('pendiente', 0)}, "
          f"en_curso={conteo.get('en_curso', 0)}, "
          f"fallido={conteo.get('fallido', 0)})")
    con.close()


def main():
    """Define el CLI con argparse y despacha al subcomando."""
    parser = argparse.ArgumentParser(
        description="Pipeline de δ de Gromov en grafos de Cayley.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_nuevo = sub.add_parser("nuevo", help="crea una corrida y encola trabajos")
    p_nuevo.add_argument("familia")
    p_nuevo.add_argument("--gens", required=True, help="G1,G2 (sin inversos)")
    fuente = p_nuevo.add_mutually_exclusive_group(required=True)
    fuente.add_argument("--p", help="COTA o lista de primos: 13 | 3,5,7")
    fuente.add_argument("--n", help="lista o rango de enteros: 3-9 | 4,6,8")
    p_nuevo.add_argument("--e", default=None,
                         help="exponente(s): K | A-B (omiso = 1)")
    p_nuevo.add_argument("--img", default=None,
                         help="extremos | todos | lista/rango de params "
                              "(omiso: no se genera ninguna imagen)")
    p_nuevo.set_defaults(func=cmd_nuevo)

    p_correr = sub.add_parser("correr", help="ejecuta la cola de una corrida")
    p_correr.add_argument("carpeta")
    p_correr.set_defaults(func=cmd_correr)

    p_estado = sub.add_parser("estado", help="muestra hechos/total")
    p_estado.add_argument("carpeta")
    p_estado.set_defaults(func=cmd_estado)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()