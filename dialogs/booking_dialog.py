# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.dialogs import WaterfallDialog, WaterfallStepContext, DialogTurnResult
from botbuilder.dialogs.prompts import ConfirmPrompt, TextPrompt, PromptOptions
from botbuilder.core import MessageFactory
from .cancel_and_help_dialog import CancelAndHelpDialog
from .date_resolver_dialog import DateResolverDialog


class BookingDialog(CancelAndHelpDialog):
    """Flight booking implementation."""

    def __init__(self, logs, dialog_id: str = None):
        super(BookingDialog, self).__init__(dialog_id or BookingDialog.__name__)
        text_prompt = TextPrompt(TextPrompt.__name__)
        waterfall_dialog = WaterfallDialog(
            WaterfallDialog.__name__,
            [
                self.from_city_step,
                self.to_city_step,
                self.from_date_step,
                self.to_date_step,
                self.budget_step,
                self.confirm_step,
                self.final_step,
            ]
        )
        self.add_dialog(text_prompt)
        self.add_dialog(ConfirmPrompt(ConfirmPrompt.__name__))
        self.add_dialog(
            DateResolverDialog(
                DateResolverDialog.__name__ + "_from_date",
                "When do you want to leave?"
            )
        )
        self.add_dialog(
            DateResolverDialog(
                DateResolverDialog.__name__ + "_to_date",
                "When do you want to come back?"
            )
        )
        self.add_dialog(waterfall_dialog)
        self.initial_dialog_id = WaterfallDialog.__name__
        self._logs = logs

    async def from_city_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for from_city."""
        booking_details = step_context.options

        if not booking_details.from_city:
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(prompt=MessageFactory.text("From what city will you be departing?"))
            )

        return await step_context.next(booking_details.from_city)

    async def to_city_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for to_city."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.from_city = step_context.result

        if not booking_details.to_city:
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(prompt=MessageFactory.text("To what city would you like to travel?"))
            )

        return await step_context.next(booking_details.to_city)

    async def from_date_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for travel date.
        This will use the DATE_RESOLVER_DIALOG."""

        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.to_city = step_context.result

        if not booking_details.from_date:
            return await step_context.begin_dialog(
                DateResolverDialog.__name__ + "_from_date", booking_details.from_date
            )

        return await step_context.next(booking_details.from_date)

    async def to_date_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for travel date.
        This will use the DATE_RESOLVER_DIALOG."""

        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.from_date = step_context.result

        if not booking_details.to_date:
            return await step_context.begin_dialog(
                DateResolverDialog.__name__ + "_to_date", booking_details.to_date
            )

        return await step_context.next(booking_details.to_date)

    async def budget_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for budget."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.to_date = step_context.result

        if not booking_details.budget:
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(prompt=MessageFactory.text("What is your budget?"))
            )

        return await step_context.next(booking_details.budget)
    
    async def confirm_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Confirm the information the user has provided."""
        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.budget = step_context.result

        msg = (
            "Please confirm that:\n"
            "- You want to **book a flight**.\n"
            f"- From **{booking_details.from_city}** to **{booking_details.to_city}**.\n"
            f"- Between the **{booking_details.from_date}** and the **{booking_details.to_date}**.\n"
            f"- With a budget of **{booking_details.budget}**."
        )

        # Offer a YES/NO prompt.
        return await step_context.prompt(ConfirmPrompt.__name__, PromptOptions(prompt=MessageFactory.text(msg)))

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Complete the interaction and end the dialog."""
        booking_details = step_context.options

        # TRACK THE DATA INTO Application INSIGHTS
        # more here https://docs.microsoft.com/en-us/azure/azure-monitor/app/api-custom-events-metrics
        to_log = {}
        to_log["origin"] = booking_details.from_city
        to_log["destination"] = booking_details.to_city
        to_log["departure_date"] = booking_details.from_date
        to_log["return_date"] = booking_details.to_date
        to_log["budget"] = booking_details.budget
        to_log["dialog_id"] = self.initial_dialog_id
        properties = {'custom_dimensions': to_log}

        if step_context.result:
            self._logs.logger.warning('YES answer', extra=properties)
            return await step_context.end_dialog(booking_details)
        else:
            self._logs.logger.error('NO answer', extra=properties)
        return await step_context.end_dialog()
