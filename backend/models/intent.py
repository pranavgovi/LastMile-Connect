"""Intent model: short-lived geo + time window for matching."""
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class Intent(Base):
    __tablename__ = "intents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # PostGIS points: WGS84 (lng, lat). Stored as SRID=4326;POINT(lng lat)
    origin: Mapped[str] = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    destination: Mapped[str] = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="intents")
