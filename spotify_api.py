import aiohttp
from fastapi.routing import APIRouter
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
    
    headers = {"Authorization": "Bearer BQDGQVwuh5AaHl-zsn4k32Bj1noD6p65XFPriSrvK-f2OopBxcC5LzqXT3Wb9GcUTbmoWoQ9T6yHV2uG09pr1ldXvSmyWqif-4XTlao0knrZSxnAXAE2_Ub4k9dlFPYsxVroNEO7nKyg15UdADzgCYaSXVTBN2XdCC5ay_XvHQtp0d0vdnkLexZeuPsTp5dz1yJ8AqbYmJP2r2QXAiO79Zqhd-JWUMytKXC29libvzJK_9xr9Hc"}
    
    # Buscar la canción
    async with httpx.AsyncClient() as client:
        search_url = "https://api.spotify.com/v1/search"
        params = {"q": track_name +" "+ artist, "type": "track", "limit": 1}
        response = await client.get(search_url, headers=headers, params=params)
        print(response.json())
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
    try:
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
            print(f"[4] Datos completos: {data}")
            return data
    except Exception as e:
        print(f"[ERROR] En find_spotify: {str(e)}")
        raise
        
                   
            