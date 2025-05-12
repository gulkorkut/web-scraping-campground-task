from fastapi import FastAPI, HTTPException
import asyncio
from main import main  

app = FastAPI()

@app.get("/start-scraper")
async def start_scraper():
    """
    Scraper'ı tetikleyen API endpoint'i.
    """
    try:
        
        await main()  
        return {"status": "Scraper started successfully!"}
    except Exception as e:
        
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
