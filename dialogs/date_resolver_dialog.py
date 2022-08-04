# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from datatypes_date_time.timex import Timex

from botbuilder.core import MessageFactory
from botbuilder.dialogs import WaterfallDialog, DialogTurnResult, WaterfallStepContext
from botbuilder.dialogs.prompts import (
    DateTimePrompt,
    PromptValidatorContext,
    PromptOptions,
    DateTimeResolution,
)
from .cancel_and_help_dialog import CancelAndHelpDialog


class DateResolverDialog(CancelAndHelpDialog):
    """Resolve the date"""

    def __init__(self, dialog_id: str = None, prompt_msg: str = "On what date would you like to travel?"):
        super(DateResolverDialog, self).__init__(dialog_id or DateResolverDialog.__name__)

        date_time_prompt = DateTimePrompt(DateTimePrompt.__name__, DateResolverDialog.datetime_prompt_validator)

        waterfall_dialog = WaterfallDialog(
            WaterfallDialog.__name__ + "2", [self.initial_step, self.final_step]
        )

        self.add_dialog(date_time_prompt)
        self.add_dialog(waterfall_dialog)
        self.initial_dialog_id = WaterfallDialog.__name__ + "2"
        self.prompt_msg = prompt_msg

    async def initial_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for the date."""
        timex = step_context.options

        reprompt_msg = (
            "Please enter your travel date including the day, month and the year."
        )

        if not timex:
            # We were not given any date at all so prompt the user.
            return await step_context.prompt(
                DateTimePrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text(self.prompt_msg),
                    retry_prompt=MessageFactory.text(reprompt_msg),
                )
            )

        # We have a Date we just need to check it is unambiguous.
        if "definite" in Timex(timex).types:
            # This is essentially a "reprompt" of the data we were given up front.
            return await step_context.prompt(
                DateTimePrompt.__name__, PromptOptions(prompt=reprompt_msg)
            )

        return await step_context.next(DateTimeResolution(timex=timex))

    async def final_step(self, step_context: WaterfallStepContext):
        """Cleanup - set final return value and end dialog."""
        timex = step_context.result[0].timex
        return await step_context.end_dialog(timex)

    @staticmethod
    async def datetime_prompt_validator(prompt_context: PromptValidatorContext) -> bool:
        """ Validate the date provided is in proper form. """
        if prompt_context.recognized.succeeded:
            timex = prompt_context.recognized.value[0].timex.split("T")[0]

            # TODO: Needs TimexProperty
            return "definite" in Timex(timex).types

        return False
