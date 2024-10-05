from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Designate a directory that will store static files, such as the favicon.
# Reference: https://fastapi.tiangolo.com/tutorial/static-files/
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def get_greeting():
    return {"greeting": "Hello world"}
