db = db.getSiblingDB('chistes');

db.createCollection('chistes_collection');

db.chistes_collection.insertMany([
    {
       joke_text: 'helpdev'
    } 
]);