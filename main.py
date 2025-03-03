from fastapi import FastAPI
from src.services.trf6_scraping_service import Trf6ScrapingService

app = FastAPI()

trf6_scraping_service = Trf6ScrapingService()

@app.get("/")
async def root():
    return {"greeting": "Hello, World!", "message": "Welcome to FastAPI!"}


@app.get("/processo/{processo}")
async def get_processo(processo: str):
    resultado = trf6_scraping_service.consultar_processo(processo)
    return resultado