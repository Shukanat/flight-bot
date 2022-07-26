import aiounittest
import pytest
from botbuilder.core.adapters import TestAdapter

from app import BOT
from config import DefaultConfig
from flight_booking_recognizer import FlightBookingRecognizer


class BotTest(aiounittest.AsyncTestCase):
    async def test_response(self):
        adapter = TestAdapter(BOT.on_turn)
        resp = await adapter.test('Hello', expected="Where do you want to go for holidays?")


def test_luis_conf():
    CONFIG = DefaultConfig()
    RECOGNIZER = FlightBookingRecognizer(CONFIG)
    assert RECOGNIZER.is_configured
