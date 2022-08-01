from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from botbuilder.core import (
    BotFrameworkAdapterSettings,
    ConversationState,
    MemoryStorage,
    UserState)
from botbuilder.schema import Activity
from botbuilder.applicationinsights import ApplicationInsightsTelemetryClient
from botbuilder.integration.applicationinsights.aiohttp import AiohttpTelemetryProcessor
from botbuilder.core.telemetry_logger_middleware import TelemetryLoggerMiddleware
from botbuilder.core import NullTelemetryClient

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
# TELEMETRY_CLIENT = ApplicationInsightsTelemetryClient(
#     instrumentation_key=CONFIG.APPINSIGHTS_INSTRUMENTATIONKEY, 
#     telemetry_processor=AiohttpTelemetryProcessor(), 
#     client_queue_size=10)
# TELEMETRY_MIDDLEWARE = TelemetryLoggerMiddleware(
#     telemetry_client=TELEMETRY_CLIENT,
#     log_personal_information=True)
# ADAPTER.use(TELEMETRY_MIDDLEWARE)
TELEMETRY_CLIENT = None

RECOGNIZER = FlightBookingRecognizer(CONFIG, telemetry_client=TELEMETRY_CLIENT)
BOOKING_DIALOG = BookingDialog()
DIALOG = MainDialog(RECOGNIZER, BOOKING_DIALOG, telemetry_client=TELEMETRY_CLIENT)
BOT = DialogAndWelcomeBot(CONVERSATION_STATE, USER_STATE, DIALOG, TELEMETRY_CLIENT)
# TELEMETRY_CLIENT.main_dialog = DIALOG

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
