from io import StringIO
import re
from rasa.core.interpreter import NaturalLanguageInterpreter
from sanic.request import Request
from sanic import Sanic, Blueprint, response
from rasa.core import utils
from rasa.constants import DOCS_BASE_URL
import rasa.utils.endpoints
from rasa.nlu.components import Component
import asyncio
import inspect
from rasa.core.channels.channel import InputChannel
from rasa.core.channels.channel import QueueOutputChannel
from rasa.core.channels.channel import CollectingOutputChannel
from rasa.core.channels.channel import RestInput
from asyncio import Queue
from rasa.core.channels.channel import UserMessage
import json
import logging
import uuid
from asyncio import Queue, CancelledError
from typing import Text, List, Dict, Any,\
    Optional, Callable, Iterable, Awaitable


logger = logging.getLogger(__name__)


def getJsonObject(obj):
    # Returns a json string representation of the obj.
    # To prevent issues with single quotation marks, these are replaced
    # by double quotation marks if needed (not every occurance of a single
    # quotation mark maybe reblaced!).

    if (obj is None):
        return None
    jString = str(obj).replace("{'", '{"').replace("':", '":')\
        .replace(", '", ', "')\
        .replace(": '", ': "').replace("', ", '", ').replace("'}", '"}')
    print("jString: " + jString)
    return json.loads(jString)


class EchoConnector(InputChannel):
    """A custom http input channel.

    This implementation is the basis for a custom implementation of a chat
    frontend. You can customize this to send messages to Rasa Core and
    retrieve responses from the agent."""

    @classmethod
    def name(cls):
        return "echo"

    @staticmethod
    async def on_message_wrapper(
        on_new_message: Callable[[UserMessage], Awaitable[None]],
        text: Text,
        queue: Queue,
        sender_id: Text,
    ) -> None:
        collector = QueueOutputChannel(queue)

        message = UserMessage(
            text, collector, sender_id, input_channel=RestInput.name()
        )
        await on_new_message(message)

        await queue.put("DONE")  # pytype: disable=bad-return-type

    async def _extract_sender(self, req) -> Optional[Text]:
        # return req.json.get("sender", None)
        return req.json.get("session")["user"]["userId"]

    # noinspection PyMethodMayBeStatic
    def _extract_message(self, req):
        return req.json.get("message", None)

    def stream_response(
        self,
        on_new_message: Callable[[UserMessage], Awaitable[None]],
        text: Text,
        sender_id: Text,
    ) -> Callable[[Any], Awaitable[None]]:
        async def stream(resp: Any) -> None:
            q = Queue()
            task = asyncio.ensure_future(
                self.on_message_wrapper(on_new_message, text, q, sender_id)
            )
            while True:
                result = await q.get()  # pytype: disable=bad-return-type
                if result == "DONE":
                    break
                else:
                    await resp.write(json.dumps(result) + "\n")
            await task

        return stream  # pytype: disable=bad-return-type

    def blueprint(self, on_new_message: Callable[[UserMessage],
                                                 Awaitable[None]]):
        custom_webhook = Blueprint(
            "custom_webhook_{}".format(type(self).__name__),
            inspect.getmodule(self).__name__,
        )

        # noinspection PyUnusedLocal
        @custom_webhook.route("/", methods=["GET"])
        async def health(request: Request):
            return response.json({"status": "ok"})

        @custom_webhook.route("/webhook", methods=["POST"])
        async def receive(request: Request):
            print(f"dumping request: {request}")
            print(request.json)
            sender_id = await self._extract_sender(request)
            # sender_id = request.json.get("session")["user"]["userId"]
            print("sender_id: "+sender_id)
            req = request.json.get("request")
            should_use_stream = rasa.utils.endpoints.bool_arg(
                request, "stream", default=False
            )

            if should_use_stream:
                return response.stream(
                    self.stream_response(on_new_message, req, sender_id),
                    content_type="text/event-stream",
                )
            else:
                collector = CollectingOutputChannel()
                # noinspection PyBroadException
                try:
                    await on_new_message(
                        UserMessage(
                            json.dumps(req), collector, sender_id,
                            input_channel=self.name()
                        )
                    )
                except CancelledError:
                    logger.error(
                        "Message handling timed out for "
                        "user message '{}'.".format(req)
                    )
                except Exception:
                    logger.exception(
                        "An exception occured while handling "
                        "user message '{}'.".format(req)
                    )
                # return response.json(collector.messages)
                return response.json(mapp2Echo(collector.messages))

        def mapp2Echo(messages):
            print("message:")
            print(messages)
            print("messages[0]")
            print(messages[0])
            msg = getJsonObject(messages[0])
            answer = msg.get("text")
            print("answer: " + answer)
            return {
                "version": "0.1",
                "sessionAttributes": {
                    "status": "test"
                },
                "response": {
                    "outputSpeech": {
                        "type": "PlainText",
                        "text": answer,
                        "playBehavior": "REPLACE_ENQUEUED"
                    },
                    "reprompt": {
                        "outputSpeech": {
                            "type": "PlainText",
                            "text": answer,
                            "playBehavior": "REPLACE_ENQUEUED"
                        }
                    },
                    "shouldEndSession": "false"
                }
            }

        return custom_webhook


class EchoNLUMapper(Component):
    """Mapping echo json to Rasa intents and entities"""

    name = "EchoNLUMapper"
    provides = ["entities"]
    requires = []
    defaults = {}
    language_list = ["en"]

    def __init__(self, component_config=None):
        print("initialize, __init__")
        super(EchoNLUMapper, self).__init__(component_config)
        print("init of super called")

    def train(self, training_data, cfg, **kwargs):
        """Not needed, because the the model will be trained on echo side"""
        pass

    def convert_to_rasa(self, value, confidence):
        """Convert model output into the Rasa NLU compatible output format."""
        print("convert_to_rasa")
        entity = {"value": value,
                  "confidence": confidence,
                  "entity": "echonlu",
                  "extractor": "echonlu_mapper"}

        return entity

    def extractEntities(self, slots):
        # for slotKey, slotVal in slots.items():
        #     print(slotKey)
        #     value = slotVal.get("value", None)
        #     print(value)
        print("extractEntities")
        return [{"value": slotVal.get("value", None),
                 "confidence": 1.0,
                 "entity": slotKey,
                 "extractor": "echo2rasa"}
                for slotKey, slotVal in slots.items()]

    def process(self, message, **kwargs):
        """Retrieve the text message, pass it to the classifier
            and append the prediction results to the message class."""

        # sid = SentimentIntensityAnalyzer()
        # res = sid.polarity_scores(message.text)
        # key, value = max(res.items(), key=lambda x: x[1])

        # entity = self.convert_to_rasa(key, value)
        print("EchoNLUMapper performing mapping")
        print("message:" + message.text)
        msg = json.loads(message.text)
        msgType = msg.get("type")
        if (msgType == "LaunchRequest"):
            intentName = "greet"
        else:
            intent = getJsonObject(msg.get("intent"))
            intentName = intent.get("name")
            slots = getJsonObject(intent.get("slots"))
            print("slots:")
            print(slots)
            if (slots is not None):
                entities = self.extractEntities(slots)
                print("entities")
                print(entities)
                message.set("entities", entities, add_to_output=True)

        print("intentName: ", intentName)
        message.set("intent", {"name": intentName,
                               "confidence": 1.0}, add_to_output=True)

        # return {
        #     "text": message_text,
        #     "intent": {"name": intent, "confidence": confidence},
        #     "intent_ranking": [{"name": intent, "confidence": confidence}],
        #     "entities": entities,
        # }

    def persist(self, model_dir, model_name):
        """Pass because a pre-trained model is already persisted"""

        pass
