import aiohttp
count=0
# from fastapi.exceptions import Excep
models=["google/gemma-3-27b-it:free","meta-llama/llama-4-scout:free","meta-llama/llama-4-maverick:free"]
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
                                .En caso de que no reconozcas un valor asignar null (sin comillas, como valor JSON nulo).OJO, Solod evuelve exactamente ese formato, no le ahgas ninguna descripcion o respodnas de mas"""
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
    
async def get_data_from_image_structured_output(session:aiohttp.ClientSession,url:str,api_router_key:str):
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
                                "text": """Eres un analista cultural y musicólogo. Analiza la imagen proporcionada, teniendo en cuenta un tono cliche y muy juzogn y humoristico y determina:
1. La región geográfica y país probable
2. El clima y condiciones ambientales presentes
3. Los elementos culturales y religiosos visibles o implícitos
4. El ambiente general, estilo, tono emocional y cualquier elemento característico presente
5. Basándote en todo lo anterior, genera una lista de exactamente 10 canciones (título - artista - álbum) que representen el ambiente, estilo y contexto cultural identificado.

"""
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
          "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "music_recommendations",
      "strict": True,
      "schema": {
        "type": "object",
        "properties": {
          "data": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "track": {
                  "type": "string",
                  "description": "Nombre de la canción"
                },
                "artist": {
                  "type": "string",
                  "description": "Nombre del artista"
                },
                "album": {
                  "type": "string",
                  "description": "Nombre del álbum"
                }
              },
              "required": ["track", "artist", "album"],
              "additionalProperties": False
            }
          },
          "info": {
            "type": "string",
            "properties": {
              "explanation": {
                "type": "string",
                "description": "Explicación detallada sobre el pq de tu analisis y asignacion de canciones"
              },
              "region": {
                "type": "string",
                "description": "Región geográfica identificada"
              },
              "climate": {
                "type": "string",
                "description": "Clima y condiciones ambientales"
              },
              "culture": {
                "type": "string",
                "description": "Elementos culturales y religiosos"
              },
              "vibe": {
                "type": "string",
                "description": "Ambiente y tono emocional general"
              }
            },
            "required": ["region", "climate", "culture", "vibe"],
            "additionalProperties": False
          }
        },
        "required": ["data", "info"],
        "additionalProperties": False
      }
    }
  },
                "temperature": 0.7,  
                "max_tokens": 1024,  
                "stream": False      
            }
        ) as response:
            ai_response = await response.json()
            # print(ai_response)
            if response.status != 200:
                print(f"Error API: {response.status}, {ai_response}")
                raise Exception(f"Error en la API: {ai_response.get('error', {}).get('message', str(ai_response))}")
            
            return ai_response
    except Exception as e:
        print(f"Error en solicitud AI: {str(e)}")
        raise
      
      
async def get_recommendations(session:aiohttp.ClientSession,type:str,api_router_key:str,url:str, music_history:list):
    string_list = "\n".join([f"{music['name']}" for music in music_history])
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
                                "text": f"""Eres un analista cultural y musicólogo. Analiza la imagen proporcionada, teniendo en cuenta un tono cliche y muy juzogn y humoristico y determina:
1. La región geográfica y país probable
2. El clima y condiciones ambientales presentes
3. Los elementos culturales y religiosos visibles o implícitos
4. El ambiente general, estilo, tono emocional y cualquier elemento característico presente
5. Basándote en todo lo anterior y en esta lista sobre lo mas escuchado del usuario {music_history} , genera una lista de exactamente 10 canciones (título - artista - álbum) que representen el ambiente, estilo, contexto cultural identificado y se alineen con el tipo d emusica que escucha el usuario(Trata de que las canciones sean aproximadamente %25 posibles que las haya escuchado y %75 posibles que no para lograr mas variedad ).

"""
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
          "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "music_recommendations",
      "strict": True,
      "schema": {
        "type": "object",
        "properties": {
          "data": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "track": {
                  "type": "string",
                  "description": "Nombre de la canción"
                },
                "artist": {
                  "type": "string",
                  "description": "Nombre del artista"
                },
                "album": {
                  "type": "string",
                  "description": "Nombre del álbum"
                }
              },
              "required": ["track", "artist", "album"],
              "additionalProperties": False
            }
          },
          "info": {
            "type": "string",
            "properties": {
              "explanation": {
                "type": "string",
                "description": "Explicación detallada sobre el pq de tu analisis y asignacion de canciones"
              },
              "region": {
                "type": "string",
                "description": "Región geográfica identificada"
              },
              "climate": {
                "type": "string",
                "description": "Clima y condiciones ambientales"
              },
              "culture": {
                "type": "string",
                "description": "Elementos culturales y religiosos"
              },
              "vibe": {
                "type": "string",
                "description": "Ambiente y tono emocional general"
              }
            },
            "required": ["region", "climate", "culture", "vibe"],
            "additionalProperties": False
          }
        },
        "required": ["data", "info"],
        "additionalProperties": False
      }
    }
  },
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