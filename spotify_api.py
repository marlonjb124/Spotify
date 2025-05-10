import aiohttp
from fastapi.routing import APIRouter
from fastapi import HTTPException
import httpx

from schema import SimplifiedTrackResponse,Album,Artist,Track
# from aiocircuitbreaker import circuit
spotify = APIRouter()


SPOTIFY_API_URL = "https://api.spotify.com/v1/search"

@spotify.put("/stop")
async def stop_song():

    play_url = f"https://api.spotify.com/v1/me/player/pause?device_id=01f57fb8045a8e484c44192a94e8527ed811a87d"


    
    async with httpx.AsyncClient() as client:
        response = await client.put(play_url, headers=headers)
        # print(response.json())
    
    if response.status_code != 204:
        raise HTTPException(status_code=400, detail="Error al pausar. ¿El dispositivo está activo?")
    
    return {"status": "¡Reproduciendo!", "track_uri": track_uri}
@spotify.put("/play")
async def play_song(track_name: str,artist:str,):
    # if not tokens.get("access_token"):
    #     raise HTTPException(status_code=401, detail="No autenticado. Ve a /login primero.")
    
    headers = {"Authorization": "Bearer BQA6WX0Qe2M61oJQ1CHNg_2c06u8Rt2L7RvwSurvkEhrIU3ksOTUGqWgVy0x6wf17pWgVPpIPv-Efj-8jjFNgBY01TAPmSq0PEwhDqEi9EQxdmHyY5jKWhO0F2Zl465rgSyNK8mkyzy8EfMhFgwQC3vP_hFrjAKFcgq-UYj8loguMdTeoLSJYpYg5Id5WXlOOpp7ZaWaddtS01zcDTBo0mg5EuZMO80RYUbucbtRPdOpjaJ8AqSBR9g"}
    
    # Buscar la canción
    async with httpx.AsyncClient() as client:
        search_url = "https://api.spotify.com/v1/search"
        params = {"q": track_name +" "+ artist, "type": "track", "limit": 1}
        response = await client.get(search_url, headers=headers, params=params)
   
    if not response.json().get("tracks", {}).get("items"):
        raise HTTPException(status_code=404, detail="Canción no encontrada")
    
    track_uri = response.json()["tracks"]["items"][0]["uri"]
    
    # Obtener dispositivo activo
    # async with httpx.AsyncClient() as client:
    #     devices_url = "https://api.spotify.com/v1/me/player/devices"
    #     response = await client.get(devices_url, headers=headers)
    #     print(response.json())
    #     print(response.headers)
    
    # devices = response.json().get("devices", [])

    # if not devices:
    #     raise HTTPException(status_code=400, detail="Activa un dispositivo en Spotify primero (ej: app móvil o web).")
    
    # device_id = devices[0]["id"]
    
    # Reproducir
    play_url = f"https://api.spotify.com/v1/me/player/play"
    data = {"uris": [track_uri],"position_ms":100
}
    
    async with httpx.AsyncClient() as client:
        response = await client.put(play_url, headers=headers, json=data)

    
    if response.status_code != 204:
        raise HTTPException(status_code=400, detail="Error al reproducir. ¿El dispositivo está activo?")
    
    return {"status": "¡Reproduciendo!", "track_uri": track_uri}

@spotify.get("/track_history")
async def track_history(token:str,type:str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        devices_url = f"https://api.spotify.com/v1/me/top/{type}"
        response = await client.get(devices_url, headers=headers)
        # print(response.json())
        # print(response.headers)
        return response.json()
    


async def find_spotify_user(token:str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        devices_url = "https://api.spotify.com/v1/me/"
        response = await client.get(devices_url, headers=headers)
        print(response.json())
        print(response.headers)
        return response.json()
    
async def find_spotify(session: aiohttp.ClientSession, spotify_token: str, ai_response: dict):
    print("[1] Iniciando búsqueda en Spotify")
    # if type =="album":
    #     q = f"{ai_response['album_name']} {ai_response['authors_name'][0]}"
    # elif type =="track":
    #     q = f"{ai_response['track_name']} {ai_response['artist_name'][0]}"
    # elif type =="artist":
    #     q = f"{ai_response['artist_name']}"
    try:
        # print("Q: ",q)
        # print("type: ",type)
        print(f"[2] Estado de la sesión: {session.closed}")  # Debe ser False
        async with session.get(
            SPOTIFY_API_URL,
            headers={"Authorization": f"Bearer {spotify_token}"},
            params={
                "q": f"{ai_response['track']} {ai_response['artist']}",
                "type": "track",
                "limit": 1
            }
        ) as response:
            print(f"[3] Respuesta recibida. Estado HTTP: {response.status}")
            data = await response.json()
            print("devolviendo data de spotify")
            # print(data)
            return data
    except Exception as e:
        print(f"[ERROR] En find_spotify: {str(e)}")
        raise
def transform_spotify_response(spotify_data: dict) -> SimplifiedTrackResponse:
    """
    Transforms the raw Spotify API response into our simplified format.
    
    Args:
        spotify_data: Raw response from Spotify API
        
    Returns:
        SimplifiedTrackResponse: Cleaned and structured data
    """
    if not spotify_data.get('tracks', {}).get('items'):
        raise ValueError("No track data found in Spotify response")
    
    track_data = spotify_data['tracks']['items'][0]
    
    return SimplifiedTrackResponse(
        track=Track.from_spotify(track_data),
        album=Album.from_spotify(track_data['album']),
        artists=[Artist.from_spotify(artist) for artist in track_data['artists']]
    )
        
                   
            