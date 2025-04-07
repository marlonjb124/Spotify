from sqlalchemy import  Column, ForeignKey, Integer, String,UniqueConstraint,DateTime,Boolean
from sqlalchemy.orm import relationship,mapped_column,Mapped
from database import Base
# from datetime import datetime
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
    # email: Mapped[str] = mapped_column(String, unique=True, index=True)
    token: Mapped[str] = mapped_column(String,unique=True)
    username:Mapped[str] = mapped_column(String, unique=True, index=True)
    # password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # profile = relationship("Profile", uselist=False, back_populates="user",lazy="joined")
    # rol=relationship("Rol",secondary="user_roles",back_populates="useRol",lazy="joined")