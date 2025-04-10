from pydantic import BaseModel
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class Image(BaseModel):
    """Spotify image resource"""
    url: str
    height: Optional[int] = None
    width: Optional[int] = None

class Artist(BaseModel):
    """Simplified artist representation"""
    name: str
    external_url: str
    images: List[Image] = []
    
    @classmethod
    def from_spotify(cls, artist_data: dict) -> 'Artist':
        return cls(
            name=artist_data['name'],
            external_url=artist_data['external_urls']['spotify'],
            images=artist_data.get('images', [])
        )

class Album(BaseModel):
    """Simplified album representation"""
    name: str
    external_url: str
    images: List[Image]
    release_date: str
    total_tracks: int
    
    @classmethod
    def from_spotify(cls, album_data: dict) -> 'Album':
        return cls(
            name=album_data['name'],
            external_url=album_data['external_urls']['spotify'],
            images=album_data.get('images', []),
            release_date=album_data['release_date'],
            total_tracks=album_data['total_tracks']
        )

class Track(BaseModel):
    """Simplified track representation"""
    name: str
    external_url: str
    duration_ms: int
    explicit: bool
    popularity: int
    preview_url: Optional[str] = None
    images: List[Image] = []
    
    @classmethod
    def from_spotify(cls, track_data: dict) -> 'Track':
        # Use album images if track has no specific images
        images = track_data.get('images', track_data['album'].get('images', []))
        return cls(
            name=track_data['name'],
            external_url=track_data['external_urls']['spotify'],
            duration_ms=track_data['duration_ms'],
            explicit=track_data['explicit'],
            popularity=track_data['popularity'],
            preview_url=track_data.get('preview_url'),
            images=images
        )

class SimplifiedTrackResponse(BaseModel):
    """Final simplified response structure"""
    track: Track
    album: Album
    artists: List[Artist]
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
    id: int = None
    is_active: bool = True
    # rol:List[Rol]=[]
    class Config:
        from_attributes = True
class UserReturn(User):
    teams:list["TeamBase"] = []
    teams_created:list["TeamBase"] = []