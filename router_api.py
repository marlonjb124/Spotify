import aiohttp
# from fastapi.exceptions import Excep
async def get_data_from_image(session:aiohttp.ClientSession,url:str,api_router_key:str):
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
        "Authorization": f"Bearer {api_router_key}",
        "Content-Type": "application/json"
    },
                json={
        "model": "google/gemma-3-27b-it:free",
        "messages": [
        {
            "role": "user",
            "content": [
            {
                "type": "text",
                "text": """Necesito que me extraigas de la imagen los playlist,artistas,album,canciones y me lo devuelvas un json con la siguiente estructura  [{\"track\": \"track_name\", \"artist\": \"artist_name\", \"album\": \"album_name\"}]
                .En caso de que no reconozcas un valor asignar Null. En caso de q la iamgen no tenga nada q ver con spotify y esten fuera de contexto solo devolver la palabra \"Null\" en la respuesta."""
            },
            {
                "type": "image_url",
                "image_url": {
                "url": f"{url}"
                }
            }
            ]
        }
        ],
    
  }
        ) as response:
                ai_response = await response.json()
                if response.status != 200:
                    raise Exception(f"Error en modelo {model_name}: {ai_response}")
                print(ai_response)
                return ai_response
    