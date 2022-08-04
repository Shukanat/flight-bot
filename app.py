from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer
from opencensus.trace.span import SpanKind
from opencensus.trace.attributes_helper import COMMON_ATTRIBUTES

from botbuilder.core import (
    BotFrameworkAdapterSettings,
    ConversationState,
    MemoryStorage,
    UserState)
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

HTTP_URL = COMMON_ATTRIBUTES['HTTP_URL']
HTTP_STATUS_CODE = COMMON_ATTRIBUTES['HTTP_STATUS_CODE']

exporter = AzureExporter(connection_string=f"InstrumentationKey={CONFIG.APPINSIGHTS_INSTRUMENTATIONKEY}")
handler = AzureLogHandler(connection_string=f"InstrumentationKey={CONFIG.APPINSIGHTS_INSTRUMENTATIONKEY}")
sampler = ProbabilitySampler(1.0)

# fastapi middleware for opencensus
@app.middleware("http")
async def middlewareOpencensus(request: Request, call_next):  
    tracer = Tracer(exporter=exporter, sampler=sampler)       
    with tracer.span("main") as span:
        span.span_kind = SpanKind.SERVER
        response = await call_next(request)

        tracer.add_attribute_to_current_span(
            attribute_key=HTTP_STATUS_CODE,
            attribute_value=response.status_code)
        tracer.add_attribute_to_current_span(
            attribute_key=HTTP_URL,
            attribute_value=str(request.url))
    return response


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
