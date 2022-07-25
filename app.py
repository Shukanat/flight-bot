from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from botbuilder.core import (
    BotFrameworkAdapterSettings,
    ConversationState,
    MemoryStorage,
    UserState,
)
from botbuilder.schema import Activity

from config import DefaultConfig
from dialogs import MainDialog, BookingDialog
from bots import DialogAndWelcomeBot

from adapter_with_error_handler import AdapterWithErrorHandler
from flight_booking_recognizer import FlightBookingRecognizer

CONFIG = DefaultConfig()
SETTINGS = BotFrameworkAdapterSettings(CONFIG.APP_ID, CONFIG.APP_PASSWORD)
MEMORY = MemoryStorage()
USER_STATE = UserState(MEMORY)
CONVERSATION_STATE = ConversationState(MEMORY)
ADAPTER = AdapterWithErrorHandler(SETTINGS, CONVERSATION_STATE)
RECOGNIZER = FlightBookingRecognizer(CONFIG)
BOOKING_DIALOG = BookingDialog()
DIALOG = MainDialog(RECOGNIZER, BOOKING_DIALOG)
BOT = DialogAndWelcomeBot(CONVERSATION_STATE, USER_STATE, DIALOG)


app = FastAPI()

@app.post("/api/messages")
async def messages(req: Request):
    if "application/json" in req.headers["content-type"]:
        body = await req.json()
        auth_header = req.headers["authorization"] if "authorization" in req.headers else ""
    else:
        return JSONResponse(status_code=415, content={"message": "Unsupported media type"})
    
    activity = Activity().deserialize(body)
    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return JSONResponse(status_code=response.status, content=response.body)
    return JSONResponse(status_code=200, content={'message': 'OK'})
