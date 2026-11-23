"""Client identity within a firm; accounting configuration belongs to DB-02."""

from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKeyConstraint,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from lastro.core.models import Base


class Client(Base):
    """Firm-scoped client with an access version for future authorization flows."""

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
    )

    escritorio_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    nome: Mapped[str] = mapped_column(Text)
    cnpj_normalizado: Mapped[str] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(server_default=text("true"))
    versao_acesso: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
