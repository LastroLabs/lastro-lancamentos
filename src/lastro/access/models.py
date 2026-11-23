"""Identity and portfolio models; physical names follow the DB-01 exception."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from lastro.core.models import Base


class Firm(Base):
    """Accounting firm that scopes memberships and clients."""

    __tablename__ = "escritorio"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    nome: Mapped[str] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(server_default=text("true"))


class User(Base):
    """Global user identity, optionally awaiting a credential."""

    __tablename__ = "usuario"
    __table_args__ = (UniqueConstraint("identificador_login"),)

    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    identificador_login: Mapped[str] = mapped_column(Text)
    nome: Mapped[str] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(server_default=text("true"))
    credencial_hash: Mapped[str | None] = mapped_column(Text)


class Member(Base):
    """User membership and role within a firm."""

    __tablename__ = "membro"
    __table_args__ = (
        ForeignKeyConstraint(
            ["escritorio_id"],
            ["escritorio.id"],
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        UniqueConstraint("escritorio_id", "usuario_id"),
        CheckConstraint("papel IN ('chefe', 'contador')", name="papel"),
        Index(None, "usuario_id"),
    )

    escritorio_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    usuario_id: Mapped[UUID]
    papel: Mapped[str] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(server_default=text("true"))


class Session(Base):
    """Server-side session bound to a membership."""

    __tablename__ = "sessao"
    __table_args__ = (
        ForeignKeyConstraint(
            ["escritorio_id", "membro_id"],
            ["membro.escritorio_id", "membro.id"],
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        UniqueConstraint("hash_token"),
        CheckConstraint("expira_em > criada_em", name="validade"),
        Index(None, "escritorio_id", "membro_id"),
    )

    escritorio_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    membro_id: Mapped[UUID]
    hash_token: Mapped[str] = mapped_column(Text)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    encerrada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Invitation(Base):
    """Hashed invitation, with at most one pending invitation per membership."""

    __tablename__ = "convite"
    __table_args__ = (
        ForeignKeyConstraint(
            ["escritorio_id", "membro_id"],
            ["membro.escritorio_id", "membro.id"],
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["escritorio_id", "criado_por"],
            ["membro.escritorio_id", "membro.id"],
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        UniqueConstraint("hash_token"),
        CheckConstraint("hash_token ~ '^[0-9a-f]{64}$'", name="hash_token"),
        CheckConstraint("expira_em > criado_em", name="validade"),
        CheckConstraint(
            "usado_em IS NULL OR revogado_em IS NULL", name="uso_revogacao"
        ),
        Index(None, "escritorio_id", "membro_id"),
        Index(None, "escritorio_id", "criado_por"),
        Index(
            "uq_convite_escritorio_id_membro_id_pendente",
            "escritorio_id",
            "membro_id",
            unique=True,
            postgresql_where=text("usado_em IS NULL AND revogado_em IS NULL"),
        ),
    )

    escritorio_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    membro_id: Mapped[UUID]
    hash_token: Mapped[str] = mapped_column(Text)
    criado_por: Mapped[UUID]
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Assignment(Base):
    """Historical client assignment, with one open responsible membership."""

    __tablename__ = "atribuicao"
    __table_args__ = (
        ForeignKeyConstraint(
            ["escritorio_id", "cliente_id"],
            ["cliente.escritorio_id", "cliente.id"],
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["escritorio_id", "membro_id"],
            ["membro.escritorio_id", "membro.id"],
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["escritorio_id", "atribuido_por"],
            ["membro.escritorio_id", "membro.id"],
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        ),
        CheckConstraint("fim IS NULL OR fim > inicio", name="intervalo"),
        Index(None, "escritorio_id", "membro_id"),
        Index(None, "escritorio_id", "atribuido_por"),
        Index(
            None,
            "escritorio_id",
            "cliente_id",
            unique=True,
            postgresql_where=text("fim IS NULL"),
        ),
    )

    escritorio_id: Mapped[UUID] = mapped_column(primary_key=True)
    cliente_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    membro_id: Mapped[UUID]
    atribuido_por: Mapped[UUID]
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
