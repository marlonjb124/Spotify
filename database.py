from sqlalchemy.orm import declarative_base,DeclarativeBase
from sqlalchemy import create_engine, event,Column,Boolean
from sqlalchemy.orm import ORMExecuteState, Session, sessionmaker, with_loader_criteria
import os
from schema import User as UserSchema
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("LOCAL_DATABASE_URL")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



Base = declarative_base()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
def create_user(user:UserSchema,db:Session):
    
    db.add(UserModel(**user.model_dump()))
    db.commit()
    return user