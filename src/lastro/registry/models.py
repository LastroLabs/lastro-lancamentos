"""Client-owned registry and accounting-plan tables."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from lastro.core.models import Base


class Client(Base):
    """Firm-scoped client with current accounting-plan configuration."""

    __tablename__ = "cliente"
    __table_args__ = (
        ForeignKeyConstraint(
            ["escritorio_id"],
            ["escritorio.id"],
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        UniqueConstraint("escritorio_id", "cnpj_normalizado"),
        CheckConstraint("versao_acesso >= 0", name="versao_acesso"),
        ForeignKeyConstraint(
            ["escritorio_id", "id", "plano_atual_id"],
            [
                "plano_contas.escritorio_id",
                "plano_contas.cliente_id",
                "plano_contas.id",
            ],
            name="fk_cliente_plano_atual",
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        *(
            ForeignKeyConstraint(
                ["escritorio_id", "id", "plano_atual_id", column],
                [
                    "conta_contabil.escritorio_id",
                    "conta_contabil.cliente_id",
                    "conta_contabil.plano_id",
                    "conta_contabil.id",
                ],
                name=f"fk_cliente_{column}",
                ondelete="NO ACTION",
                onupdate="NO ACTION",
                deferrable=False,
            )
            for column in (
                "conta_transitoria_id",
                "conta_entrada_socio_id",
                "conta_saida_socio_id",
            )
        ),
        *(
            CheckConstraint(
                f"{column} IS NULL OR plano_atual_id IS NOT NULL",
                name=f"{column}_plano",
            )
            for column in (
                "conta_transitoria_id",
                "conta_entrada_socio_id",
                "conta_saida_socio_id",
            )
        ),
    )

    escritorio_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    nome: Mapped[str] = mapped_column(Text)
    cnpj_normalizado: Mapped[str] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(server_default=text("true"))
    versao_acesso: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    plano_atual_id: Mapped[UUID | None] = mapped_column(nullable=True)
    conta_transitoria_id: Mapped[UUID | None] = mapped_column(nullable=True)
    conta_entrada_socio_id: Mapped[UUID | None] = mapped_column(nullable=True)
    conta_saida_socio_id: Mapped[UUID | None] = mapped_column(nullable=True)


class ChartOfAccounts(Base):
    """Versioned chart imported for one client."""

    __tablename__ = "plano_contas"
    __table_args__ = (
        ForeignKeyConstraint(
            ["escritorio_id", "cliente_id"],
            ["cliente.escritorio_id", "cliente.id"],
            name="fk_plano_contas_cliente",
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["escritorio_id", "importado_por"],
            ["membro.escritorio_id", "membro.id"],
            name="fk_plano_contas_importado_por_membro",
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        UniqueConstraint(
            "escritorio_id", "cliente_id", "versao", name="uq_plano_contas_versao"
        ),
        CheckConstraint("versao > 0", name="versao"),
        CheckConstraint(
            "situacao IN ('importado', 'publicado', 'substituido')", name="situacao"
        ),
    )

    escritorio_id: Mapped[UUID] = mapped_column(primary_key=True)
    cliente_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    versao: Mapped[int] = mapped_column(Integer)
    importado_por: Mapped[UUID]
    importado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    publicado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    situacao: Mapped[str] = mapped_column(Text)


class LedgerAccount(Base):
    """Account within one version of a client's chart."""

    __tablename__ = "conta_contabil"
    __table_args__ = (
        ForeignKeyConstraint(
            ["escritorio_id", "cliente_id"],
            ["cliente.escritorio_id", "cliente.id"],
            name="fk_conta_contabil_cliente",
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["escritorio_id", "cliente_id", "plano_id"],
            [
                "plano_contas.escritorio_id",
                "plano_contas.cliente_id",
                "plano_contas.id",
            ],
            name="fk_conta_contabil_plano",
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["escritorio_id", "cliente_id", "plano_id", "pai_id"],
            [
                "conta_contabil.escritorio_id",
                "conta_contabil.cliente_id",
                "conta_contabil.plano_id",
                "conta_contabil.id",
            ],
            name="fk_conta_contabil_pai",
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        UniqueConstraint(
            "escritorio_id",
            "cliente_id",
            "plano_id",
            "codigo",
            name="uq_conta_contabil_plano_codigo",
        ),
        UniqueConstraint(
            "escritorio_id",
            "cliente_id",
            "plano_id",
            "id",
            name="uq_conta_contabil_plano_id",
        ),
        UniqueConstraint(
            "escritorio_id",
            "cliente_id",
            "plano_id",
            "codigo_reduzido",
            name="uq_conta_contabil_plano_reduzido",
        ),
        CheckConstraint("tipo IN ('S', 'A')", name="tipo"),
    )

    escritorio_id: Mapped[UUID] = mapped_column(primary_key=True)
    cliente_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    plano_id: Mapped[UUID]
    codigo: Mapped[str] = mapped_column(Text)
    nome: Mapped[str] = mapped_column(Text)
    pai_id: Mapped[UUID | None]
    ativo: Mapped[bool] = mapped_column(server_default=text("true"))
    codigo_reduzido: Mapped[str | None] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(Text, server_default=text("'A'"))


class BankAccount(Base):
    """Client bank account with optional ledger mapping and coverage dates."""

    __tablename__ = "conta_bancaria"
    __table_args__ = (
        ForeignKeyConstraint(
            ["escritorio_id", "cliente_id"],
            ["cliente.escritorio_id", "cliente.id"],
            name="fk_conta_bancaria_cliente",
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["escritorio_id", "cliente_id", "conta_contabil_id"],
            [
                "conta_contabil.escritorio_id",
                "conta_contabil.cliente_id",
                "conta_contabil.id",
            ],
            name="fk_conta_bancaria_conta_contabil",
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        CheckConstraint(
            "cobertura_fim IS NULL OR cobertura_inicio IS NULL OR cobertura_fim >= cobertura_inicio",
            name="cobertura",
        ),
    )

    escritorio_id: Mapped[UUID] = mapped_column(primary_key=True)
    cliente_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    banco: Mapped[str] = mapped_column(Text)
    apelido: Mapped[str] = mapped_column(Text)
    identificacao_protegida: Mapped[str | None] = mapped_column(Text)
    moeda: Mapped[str] = mapped_column(Text, server_default=text("'BRL'"))
    conta_contabil_id: Mapped[UUID | None]
    cobertura_inicio: Mapped[date | None] = mapped_column(Date)
    cobertura_fim: Mapped[date | None] = mapped_column(Date)


class Partner(Base):
    """Fictional or real partner registered for one client at runtime."""

    __tablename__ = "socio"
    __table_args__ = (
        ForeignKeyConstraint(
            ["escritorio_id", "cliente_id"],
            ["cliente.escritorio_id", "cliente.id"],
            name="fk_socio_cliente",
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
    )

    escritorio_id: Mapped[UUID] = mapped_column(primary_key=True)
    cliente_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    nome: Mapped[str] = mapped_column(Text)
    nome_normalizado: Mapped[str] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(server_default=text("true"))
