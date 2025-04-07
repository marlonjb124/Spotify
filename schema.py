from pydantic import BaseModel

class UserBase(BaseModel):
    username: str

    class Config:
        from_attributes = True
        # arbitrary_types_allowed=True
        
        
class UserCreate(UserBase):
    token: str
    # rol:List["Rol_create"]=[Rol_create(rol=DefaultRoles.BASIC_USER_ROL)]

class User(UserBase):
    token:str
    id: int
    is_active: bool
    # rol:List[Rol]=[]
    class Config:
        from_attributes = True
class UserReturn(User):
    teams:list["TeamBase"] = []
    teams_created:list["TeamBase"] = []