"""Arquivo temporario para demonstrar o bloqueio do SAST no Tech Challenge."""

import subprocess


def executar_comando_entrada(comando: str) -> None:
    """Implementacao propositalmente insegura; nao deve chegar a main."""
    subprocess.run(comando, shell=True, check=False)
