
import sqlite3
from pathlib import Path


class Database:
    """Acesso e regras de negócio do banco de materiais."""

    STATUS_VALIDOS = (
        "Pendente",
        "Em atendimento",
        "Atendida"
    )

    PRIORIDADES_VALIDAS = ("Normal", "Alta")

    def __init__(self, caminho: str | Path = "usuario.db") -> None:
        self.conn = sqlite3.connect(caminho)
        self.conn.execute("PRAGMA foreign_keys = ON")

        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS materiais (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setor TEXT NOT NULL,
                    material TEXT NOT NULL,
                    quantidade INTEGER NOT NULL CHECK(quantidade > 0),
                    prioridade TEXT NOT NULL
                        CHECK(prioridade IN ('Normal', 'Alta')),
                    status TEXT NOT NULL DEFAULT 'Pendente'
                        CHECK(status IN (
                            'Pendente',
                            'Em atendimento',
                            'Atendida'
                        )),
                    data_hora TEXT NOT NULL
                        DEFAULT (datetime('now', 'localtime'))
                )
            """)

            self.migrar_banco()

    # MIGRAR BANCO DE DADOS
    def migrar_banco(self) -> None:
        """Atualiza bancos antigos sem perder os materiais cadastrados."""

        colunas = self.conn.execute(
            "PRAGMA table_info(materiais)"
        ).fetchall()

        nomes_colunas = [coluna[1] for coluna in colunas]

        if "status" not in nomes_colunas:
            self.conn.execute("""
                ALTER TABLE materiais
                ADD COLUMN status TEXT NOT NULL DEFAULT 'Pendente'
            """)
            nomes_colunas.append("status")

        if "data_hora" not in nomes_colunas:
            self.conn.execute("""
                ALTER TABLE materiais
                ADD COLUMN data_hora TEXT
            """)

            self.conn.execute("""
                UPDATE materiais
                SET data_hora = datetime('now', 'localtime')
                WHERE data_hora IS NULL OR data_hora = ''
            """)

            nomes_colunas.append("data_hora")

        sql_tabela = self.conn.execute("""
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table' AND name = 'materiais'
        """).fetchone()[0]

        sql_normalizado = sql_tabela.lower() if sql_tabela else ""

        possui_fluxo_novo = (
            "em atendimento" in sql_normalizado
            and "atendida" in sql_normalizado
        )

        if not possui_fluxo_novo:
            self.conn.execute(
                "DROP TABLE IF EXISTS materiais_nova"
            )

            self.conn.execute("""
                CREATE TABLE materiais_nova (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setor TEXT NOT NULL,
                    material TEXT NOT NULL,
                    quantidade INTEGER NOT NULL CHECK(quantidade > 0),
                    prioridade TEXT NOT NULL
                        CHECK(prioridade IN ('Normal', 'Alta')),
                    status TEXT NOT NULL DEFAULT 'Pendente'
                        CHECK(status IN (
                            'Pendente',
                            'Em atendimento',
                            'Atendida'
                        )),
                    data_hora TEXT NOT NULL
                        DEFAULT (datetime('now', 'localtime'))
                )
            """)

            self.conn.execute("""
                INSERT INTO materiais_nova (
                    id,
                    setor,
                    material,
                    quantidade,
                    prioridade,
                    status,
                    data_hora
                )
                SELECT
                    id,
                    setor,
                    material,
                    quantidade,
                    prioridade,
                    CASE
                        WHEN status IN (
                            'Pendente',
                            'Em atendimento',
                            'Atendida'
                        ) THEN status
                        WHEN status = 'Concluído' THEN 'Atendida'
                        ELSE 'Pendente'
                    END,
                    COALESCE(
                        NULLIF(data_hora, ''),
                        datetime('now', 'localtime')
                    )
                FROM materiais
            """)

            self.conn.execute("DROP TABLE materiais")

            self.conn.execute("""
                ALTER TABLE materiais_nova
                RENAME TO materiais
            """)

    # VALIDAR DADOS
    def validar_dados(
        self,
        setor: str,
        material: str,
        quantidade: int | str,
        prioridade: str
    ) -> tuple[str, str, int, str]:

        if not isinstance(setor, str) or not setor.strip():
            raise ValueError("O campo Setor não pode ficar vazio!")

        if not isinstance(material, str) or not material.strip():
            raise ValueError("O campo Material não pode ficar vazio!")

        if isinstance(quantidade, bool) or isinstance(quantidade, float):
            raise ValueError(
                "A quantidade deve ser um número inteiro positivo!"
            )

        try:
            quantidade = int(quantidade)
        except (ValueError, TypeError, OverflowError):
            raise ValueError(
                "A quantidade deve ser um número inteiro!"
            )

        if quantidade <= 0:
            raise ValueError(
                "A quantidade deve ser maior que zero!"
            )

        if prioridade not in self.PRIORIDADES_VALIDAS:
            raise ValueError(
                "Prioridade inválida! Use Normal ou Alta."
            )

        return (
            setor.strip(),
            material.strip(),
            quantidade,
            prioridade
        )

    # LISTAR MATERIAIS
    def listar(self) -> list[tuple]:
        cursor = self.conn.execute("""
            SELECT
                id,
                setor,
                material,
                quantidade,
                prioridade,
                status,
                data_hora
            FROM materiais
            ORDER BY id
        """)

        return cursor.fetchall()

    # INSERIR MATERIAL
    def inserir(
        self,
        setor: str,
        material: str,
        quantidade: int | str,
        prioridade: str
    ) -> None:

        setor, material, quantidade, prioridade = self.validar_dados(
            setor,
            material,
            quantidade,
            prioridade
        )

        with self.conn:
            self.conn.execute("""
                INSERT INTO materiais (
                    setor,
                    material,
                    quantidade,
                    prioridade
                )
                VALUES (?, ?, ?, ?)
            """, (
                setor,
                material,
                quantidade,
                prioridade
            ))

    # ATUALIZAR MATERIAL
    def atualizar(
        self,
        material_id: int,
        setor: str,
        material: str,
        quantidade: int | str,
        prioridade: str
    ) -> None:

        setor, material, quantidade, prioridade = self.validar_dados(
            setor,
            material,
            quantidade,
            prioridade
        )

        with self.conn:
            cursor = self.conn.execute("""
                UPDATE materiais
                SET
                    setor = ?,
                    material = ?,
                    quantidade = ?,
                    prioridade = ?
                WHERE id = ?
            """, (
                setor,
                material,
                quantidade,
                prioridade,
                material_id
            ))

            if cursor.rowcount == 0:
                raise ValueError("Material não encontrado!")

    # INICIAR ATENDIMENTO: Pendente -> Em atendimento
    def iniciar_atendimento(self, material_id: int) -> None:

        with self.conn:
            cursor = self.conn.execute("""
                UPDATE materiais
                SET status = 'Em atendimento'
                WHERE id = ? AND status = 'Pendente'
            """, (material_id,))

            if cursor.rowcount == 0:
                raise ValueError(
                    "Não é possível iniciar. O material não existe "
                    "ou não está pendente."
                )

    # CONCLUIR ATENDIMENTO: Em atendimento -> Atendida
    def concluir_atendimento(self, material_id: int) -> None:

        with self.conn:
            cursor = self.conn.execute("""
                UPDATE materiais
                SET status = 'Atendida'
                WHERE id = ? AND status = 'Em atendimento'
            """, (material_id,))

            if cursor.rowcount == 0:
                raise ValueError(
                    "Não é possível concluir. O material não existe "
                    "ou não está em atendimento."
                )

    # RETORNAR PARA PENDENTE: Em atendimento -> Pendente
    def retornar_pendente(self, material_id: int) -> None:

        with self.conn:
            cursor = self.conn.execute("""
                UPDATE materiais
                SET status = 'Pendente'
                WHERE id = ? AND status = 'Em atendimento'
            """, (material_id,))

            if cursor.rowcount == 0:
                raise ValueError(
                    "Não é possível retornar. O material não existe "
                    "ou não está em atendimento."
                )

    # EXCLUIR MATERIAL
    def excluir(self, material_id: int) -> None:

        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM materiais WHERE id = ?",
                (material_id,)
            )

            if cursor.rowcount == 0:
                raise ValueError("Material não encontrado!")

    # FECHAR BANCO
    def fechar(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None
