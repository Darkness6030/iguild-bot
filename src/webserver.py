import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from src import database
from src.config import SERVER_HOST, SERVER_PORT
from src.handlers import bot
from src.images import get_referral_image
from src.keyboards import create_play_keyboard
from src.translations import _

app = FastAPI()


@app.get("/")
async def index_route():
    return FileResponse("assets/templates/index.html")


@app.get("/share")
async def share_route():
    return FileResponse("assets/templates/share_results.html")


@app.get("/results")
async def result_route(user_id: int):
    user = database.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return FileResponse(get_referral_image(user))


@app.post("/watch_ad", status_code=204)
async def watch_ad_route(user_id: int):
    user = database.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.spins_left += 10
    database.commit()

    await bot.send_message(
        user.chat_id,
        _("watch_ad_success", user.language, anon_name=user.format_anon_name()),
        reply_markup=create_play_keyboard(user.language)
    )


async def start_server():
    config = uvicorn.Config(app, host=SERVER_HOST, port=SERVER_PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
