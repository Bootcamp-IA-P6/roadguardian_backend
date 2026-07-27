"""Carga de prompts desde ficheros .md.

Los prompts viven en .md y no dentro del código a propósito: se reescriben
constantemente, quien mejor sabe cómo debe sonar un informe no tiene por qué
programar, y así un cambio de redacción es un diff de prosa y no de Python.

Los huecos se marcan con $variable (string.Template) en vez de {variable}
(str.format) porque las llaves aparecen en cuanto un prompt incluye un ejemplo
de JSON, y .format() se atragantaría con ellas.
"""

from pathlib import Path
from string import Template

PROMPTS_DIR = Path(__file__).parent


def load(name: str) -> str:
    """Devuelve el prompt tal cual, sin renderizar."""
    ruta = PROMPTS_DIR / f"{name}.md"
    if not ruta.exists():
        disponibles = sorted(p.stem for p in PROMPTS_DIR.glob("*.md"))
        raise FileNotFoundError(
            f"No existe el prompt '{name}' en {PROMPTS_DIR}. Disponibles: {disponibles}"
        )
    return ruta.read_text(encoding="utf-8")


def render(name: str, **valores) -> str:
    """Carga un prompt y rellena sus huecos.

    Usa substitute() y no safe_substitute() a propósito: si falta una variable
    preferimos un error a mandarle al modelo un prompt con un hueco a medias.
    """
    plantilla = Template(load(name))
    try:
        return plantilla.substitute(**valores)
    except KeyError as e:
        raise KeyError(
            f"Al prompt '{name}' le falta la variable {e}. Recibidas: {sorted(valores)}"
        ) from e


def variables(name: str) -> set[str]:
    """Variables que espera un prompt. Sirve para comprobarlo en los tests."""
    return set(Template(load(name)).get_identifiers())
