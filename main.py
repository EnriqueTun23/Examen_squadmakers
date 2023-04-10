from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from pydantic import BaseModel, validator
from pymongo import MongoClient
from bson.objectid import ObjectId
from decouple import config
from typing import List
from random import randint

import requests
import numpy as np
import psycopg2
app = FastAPI()





motor_BD = config("MOTOR_BD")

print(motor_BD)

if motor_BD == 'mongo':
    # Configurar la conexión a la base de datos de MongoDB
    client = MongoClient("mongodb://admin:rootpassword@localhost:27017/")
    db = client["chistes"]
    chistes_collection = db["chistes_collection"]
else:
    # Configurar la conexión a la base de datos de postgres
    connPostgress = psycopg2.connect(
        host="localhost",
        database="chistes",
        user="admin",
        password="rootpassword"
    )


# Modelo de datos joker
class Joker(BaseModel):
    joke_text: str
    
    @validator('joke_text')
    def joke_text_length(cls, v):
        if len(v) < 10:
            raise ValueError('El texto del chiste debe tener al menos 10 caracteres.')
        return v

# Endpoint para obtener todos los chistes
@app.get('/chistes')
async def get_jokers(search: str = Query(None)):
    if search == "Chuck":
        url = "https://api.chucknorris.io/jokes/random"
    elif search == "Dad":
        url = "https://icanhazdadjoke.com/"
        headers = {"Accept": "application/json"}
    elif search is None:
        if motor_BD == 'mongo':
            # Obtener el número de chistes en la base de datos
            count = chistes_collection.count_documents({})
            # Seleccionar un número aleatorio entre 0 y el número de chistes - 1
            random_index = randint(0, count - 1)
            # Obtener el chiste en la posición seleccionada
            random_chiste = chistes_collection.find().limit(-1).skip(random_index).next()
            # Devolver el chiste aleatorio como respuesta JSON
            response = {"id": str(random_chiste["_id"]), "chiste": random_chiste["joke_text"]}
            return JSONResponse(content=response)
        else:
            # Obtener el número total de chistes en la base de datos
            cur = connPostgress.cursor()
            cur.execute("SELECT COUNT(*) FROM joker")
            count = cur.fetchone()[0]
            # Generar un número aleatorio para seleccionar un chiste de forma aleatoria
            random_index = randint(0, count - 1)
            # Obtener el chiste aleatorio de la base de datos
            cur.execute("SELECT * FROM joker LIMIT 1 OFFSET %s", (random_index,))
            joke = cur.fetchone()
            
            # Si no se encuentra ningún chiste, devolver un error 404
            if joke is None:
                raise HTTPException(status_code=404, detail="No se encontraron chistes.")
            # Devolver el chiste como respuesta JSON
            response = {
                "id": joke[0],
                "texto": joke[1]
            }
            return JSONResponse(content=response)
    else:
        return {"error": "API no valida"}
    
    response = requests.get(url, headers=headers if "headers" in locals() else {})
    return response.json() if "headers" not in locals() else {"joke": response.json()["joke"]}


# Endpoint para obtener un chiste por su ID
@app.get("/chistes/{id}")
async def get_joker(id: str):
    
    if motor_BD == 'mongo':
        chiste = chistes_collection.find_one({"_id": ObjectId(id)})
         # Si no se encuentra ningún chiste con ese ID, devolver un error 404
        if chiste is None:
            raise HTTPException(status_code=404, detail="No se encontró ningún chiste con ese ID.")
        # Devolver el usuario como respuesta JSON
        response = {"id": str(chiste["_id"]), "chiste": chiste["joke_text"]}
        return JSONResponse(content=response)
    else:
        cur = connPostgress.cursor()
        cur.execute("SELECT * FROM joker WHERE id = %s", (id,))
        chiste = cur.fetchone()

        # Si no se encuentra el usuario, devolver un error 404
        if chiste is None:
            raise HTTPException(status_code=404, detail="Chiste no encontrado.")

        # Devolver el usuario como respuesta JSON
        response = {"id": chiste[0], "texto": chiste[1]}
        return JSONResponse(content=response)


#Endpoint para sacar minimo comun (Lista minimo comun multiplo)
@app.get("/lcm")
async def lcm(numbers: List[int] = Query(None)):
    # Calcular el mínimo común múltiplo de los números utilizando numpy
    result = int(np.lcm.reduce(numbers))
    
    data = {"mínimo común múltiplo": result}
    return JSONResponse(content=data)


#Endpoint para  sumar el numero que viene en la query
@app.get("/increment")
async def increment(number: int):
    result = number + 1
    data = {"suma del numero": result}
    return JSONResponse(content=data)



# Endpoint para crear un nuevo chiste
@app.post("/chistes")
async def add_joker(joker: Joker):
    if motor_BD == 'mongo':
        # Insertar el nuevo chiste en la base de datos
        result = chistes_collection.insert_one({"joke_text": joker.joke_text})
        # Devolver el nuevo chiste como respuesta JSON
        new_chiste = chistes_collection.find_one({"_id": result.inserted_id})
        response = {"id": str(new_chiste["_id"]), "chiste": new_chiste["joke_text"]}
        return JSONResponse(content=response)
    else:
        cur = connPostgress.cursor()
        cur.execute("INSERT INTO joker (joke_text) VALUES (%s) RETURNING id, joke_text", (joker.joke_text,))
        connPostgress.commit()

        # Devolver el texto creado
        new_chiste = cur.fetchone()
        response = {"id": new_chiste[0], "texto": new_chiste[1]}
        return JSONResponse(content=response)


# Endpoint actualizar un chiste
@app.put("/chistes/{id}")
async def add_joker(id: str, joker: Joker):
    if motor_BD == 'mongo':
        # Buscar el chiste en la base de datos
        old_chiste = chistes_collection.find_one({"_id": ObjectId(id)})
        # Si no se encuentra ningún chiste con ese ID, devolver un error 404
        if old_chiste is None:
            raise HTTPException(status_code=404, detail="No se encontró ningún chiste con ese ID.")

        # Actualizar el chiste con los nuevos datos
        result = chistes_collection.update_one({"_id": ObjectId(id)}, {"$set": {"joke_text": joker.joke_text}})
        # Si no se actualizó ningún chiste, devolver un error 500
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Ocurrió un error al intentar actualizar el chiste.")
        
        # Devolver el chiste actualizado como respuesta JSON
        updated_chiste = chistes_collection.find_one({"_id": ObjectId(id)})
        response = {"id": str(updated_chiste["_id"]), "chiste": updated_chiste["joke_text"]}
        return JSONResponse(content=response)
    else:
        
        cur = connPostgress.cursor()
        
        # Verificar si el chiste existe
        cur.execute("SELECT * FROM joker WHERE id = %s", (id,))
        jokerData = cur.fetchone()
        
        if jokerData is None:
            raise HTTPException(status_code=404, detail="Chiste no encontrado.")
        
        # Actualizar el chiste
        query = "UPDATE joker SET joke_text=%s WHERE id=%s RETURNING id, joke_text"
        cur.execute(query, (joker.joke_text, id,))
        connPostgress.commit()

        response = {"message": "Actualizado"}
        return JSONResponse(content=response)


# Endpoint eliminar un chiste
@app.delete("/chistes/{id}")
async def delete_joker(id: str):
    if motor_BD == 'mongo':
        # Eliminar el chiste de la base de datos
        result = chistes_collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="No se encontró ningún chiste con ese ID.")
        
        response = {"message": "Eliminado con exito"}
        return JSONResponse(content=response, status_code=204)
    else:
        cur = connPostgress.cursor()
    
        #Eliminar el chiste de la BD
        cur.execute("DELETE FROM joker WHERE id = %s", (id,))
        connPostgress.commit()
    
    
        # Si no se eliminó ningún chiste con ese ID, devolver un error 404
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="No se encontró ningún chiste con ese ID.")
    
        response = {"message": "Eliminado con exito"}
        return JSONResponse(content=response, status_code=204)
    


