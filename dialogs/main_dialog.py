# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import json
import re

from booking_details import BookingDetails
from botbuilder.core import (BotTelemetryClient, MessageFactory,
                             NullTelemetryClient)
from botbuilder.dialogs import (DialogTurnResult, WaterfallDialog,
                                WaterfallStepContext)
from botbuilder.dialogs.prompts import PromptOptions, TextPrompt
from botbuilder.schema import Attachment, InputHints
from flight_booking_recognizer import FlightBookingRecognizer
from helpers.luis_helper import Intent, LuisHelper

from .booking_dialog import BookingDialog, CancelAndHelpDialog


class MainDialog(CancelAndHelpDialog):
    def __init__(
        self,
        luis_recognizer: FlightBookingRecognizer,
        booking_dialog: BookingDialog,
        telemetry_client: BotTelemetryClient = None
    ):
        super(MainDialog, self).__init__(MainDialog.__name__)
        self.telemetry_client = telemetry_client or NullTelemetryClient()
        text_prompt = TextPrompt(TextPrompt.__name__)
        text_prompt.telemetry_client = self.telemetry_client
        booking_dialog.telemetry_client = self.telemetry_client
        wf_dialog = WaterfallDialog("WFDialog", [self.intro_step, self.act_step, self.final_step])
        wf_dialog.telemetry_client = self.telemetry_client

        self._luis_recognizer = luis_recognizer
        self._booking_dialog_id = booking_dialog.id

        self.add_dialog(text_prompt)
        self.add_dialog(booking_dialog)
        self.add_dialog(wf_dialog)

        self.initial_dialog_id = "WFDialog"


    async def intro_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        if not self._luis_recognizer.is_configured:
            await step_context.context.send_activity(
                MessageFactory.text(
                    "NOTE: LUIS is not configured. To enable all capabilities, add 'LuisAppId', 'LuisAPIKey' and "
                    "'LuisAPIHostName' to the keyvault.",
                    input_hint=InputHints.ignoring_input,
                )
            )            
            return await step_context.next(None)
        
        message_text = (
            str(step_context.options)
            if step_context.options
            else "Where do you want to go for holidays?"
        )
        prompt_message = MessageFactory.text(
            message_text, message_text, InputHints.expecting_input
        )

        return await step_context.prompt(
            TextPrompt.__name__, PromptOptions(prompt=prompt_message)
        )

    async def act_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        if not self._luis_recognizer.is_configured:
            # LUIS is not configured, we just run the BookingDialog path with an empty BookingDetailsInstance.
            return await step_context.begin_dialog(
                self._booking_dialog_id, BookingDetails()
            )

        # Call LUIS and gather any potential booking details. (Note the TurnContext has the response to the prompt.)
        intent, luis_result = await LuisHelper.execute_luis_query(
            self._luis_recognizer, step_context.context
        )

        if intent == Intent.BOOK_FLIGHT.value and luis_result:
            # Run the BookingDialog giving it whatever details we have from the LUIS call.
            return await step_context.begin_dialog(self._booking_dialog_id, luis_result)

        if intent == Intent.GET_WEATHER.value:
            get_weather_text = "TODO: get weather flow here"
            get_weather_message = MessageFactory.text(
                get_weather_text, get_weather_text, InputHints.ignoring_input
            )
            await step_context.context.send_activity(get_weather_message)

        else:
            didnt_understand_text = (
                "Sorry, I did not understand. Can you rephrase your question?"
            )
            didnt_understand_message = MessageFactory.text(
                didnt_understand_text, didnt_understand_text, InputHints.ignoring_input
            )
            await step_context.context.send_activity(didnt_understand_message)

        return await step_context.next(None)

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        # If the child dialog ("BookingDialog") was cancelled or the user failed to confirm,
        # the Result here will be null.
        if step_context.result is not None:
            result = step_context.result

            # Now we have all the booking details call the booking service.
#            msg_txt = ("Thank you, your flight is booked. Check your email for the confirmation.")
            reservation_card = self.create_adaptive_card_attachment(result)
            response = MessageFactory.attachment(reservation_card)
#            message = MessageFactory.text(msg_txt, msg_txt, InputHints.ignoring_input)
            await step_context.context.send_activity(response)

        prompt_message = "What else can I do for you?"
        return await step_context.replace_dialog(self.id, prompt_message)


    # Create internal function
    def replace(self, templateCard: dict, data: dict):
        string_temp = str(templateCard)
        for key in data:
            pattern = "\${" + key + "}"
            string_temp = re.sub(pattern, str(data[key]), string_temp)
        return eval(string_temp)


    # Load attachment from file.
    def create_adaptive_card_attachment(self, result):
        """Create an adaptive card."""
        
        path =  "cards/bookedFlightCard.json"
        with open(path) as card_file:
            card = json.load(card_file)
        
        origin = result.from_city
        destination = result.to_city
        start_date = result.from_date
        end_date = result.to_date
        budget = result.budget

        templateCard = {
            "origin": origin, 
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "budget": budget}

        flightCard = self.replace(card, templateCard)

        return Attachment(
            content_type="application/vnd.microsoft.card.adaptive", content=flightCard)
