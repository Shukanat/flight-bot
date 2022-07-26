import pytest
import aiounittest
from app import BOT

from botbuilder.core.adapters import TestAdapter

class BotTest(aiounittest.AsyncTestCase):
    async def test_response(self):

        adapter = TestAdapter(BOT.on_turn)
        resp = await adapter.test('Hello', expected="What can I help you with today?")