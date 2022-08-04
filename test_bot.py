import aiounittest
import pytest
from botbuilder.core.adapters import TestAdapter
from fastapi.testclient import TestClient

from app import BOT, app
from config import DefaultConfig
from flight_booking_recognizer import FlightBookingRecognizer

client = TestClient(app)

class BotTest(aiounittest.AsyncTestCase):
    async def test_response(self):
        adapter = TestAdapter(BOT.on_turn)
        resp = await adapter.test('Hello', expected="Where do you want to go for holidays?")


def test_luis_conf():
    CONFIG = DefaultConfig()
    RECOGNIZER = FlightBookingRecognizer(CONFIG)
    assert RECOGNIZER.is_configured


def test_health_check():
    response = client.get("/health_check")
    assert response.status_code == 200
    assert response.json() == {"message": "Flight Bot is running"}