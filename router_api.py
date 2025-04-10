import aiohttp
count=0
# from fastapi.exceptions import Excep
models=["google/gemma-3-27b-it:free","meta-llama/llama-4-scout:free"]
async def get_data_from_image(session:aiohttp.ClientSession,url:str,api_router_key:str):
    try:
        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_router_key}",
        "Content-Type": "application/json"
            },
            json={
                "model": models[1],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Necesito que me extraigas de la imagen los playlist,artistas,album,canciones y me lo devuelvas un json con la siguiente estructura  [{"track": "track_name", "artist": "artist_name", "album": "album_name"}]
                                .En caso de que no reconozcas un valor asignar null (sin comillas, como valor JSON nulo). En caso de q la imagen no tenga nada q ver con spotify y esten fuera de contexto solo devolver la palabra "Null" en la respuesta."""
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
                "temperature": 0.7,  
                "max_tokens": 1024,  
                "stream": False      
            }
        ) as response:
            ai_response = await response.json()
            print(ai_response)
            if response.status != 200:
                print(f"Error API: {response.status}, {ai_response}")
                raise Exception(f"Error en la API: {ai_response.get('error', {}).get('message', str(ai_response))}")
            
            return ai_response
    except Exception as e:
        print(f"Error en solicitud AI: {str(e)}")
        raise