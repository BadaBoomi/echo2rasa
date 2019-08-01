# run test with
# python -m tests\test_echomodel.py

import importlib
import unittest
import echo2rasa.tools.echomodel as echomodel


class TestEchoModel(unittest.TestCase):

    def get_restaurant_intent(self, model):
        intents = model.model["interactionModel"]["languageModel"]["intents"]
        for intent in intents:
            if intent['name'] == 'request_restaurant':
                return intent
        return None

    def test_invocation_name(self):
        model = echomodel.EchoModel("test", None, None, None)
        self.assertEqual(
            model.model["interactionModel"]["languageModel"]["invocationName"],
            "test")

    def test_intents(self):
        model = echomodel.EchoModel("test", ".\\tests\\resources\\domain.yml",
                                    None, None)
        model._import_domain()
        intents = model.model["interactionModel"]["languageModel"]["intents"]
        self.assertIn({'name': 'request_restaurant', 'samples': []}, intents)

    def test_utterances(self):
        model = echomodel.EchoModel("test", ".\\tests\\resources\\domain.yml",
                                    ".\\tests\\resources\\nlu.md",
                                    None)
        model._import_domain()
        model._import_nlu_file()
        restaurant_intent = self.get_restaurant_intent(model)
        self.assertIn(
            "i am looking for any place that serves {cuisine} food for {num_people}",
            model._intent_dir['request_restaurant']['samples'])

    def test_slot_type_mapping(self):
        model = echomodel.EchoModel("test", ".\\tests\\resources\\domain.yml",
                                    ".\\tests\\resources\\nlu.md",
                                    ".\\tests\\resources\\echo_domain.yml")
        model._import_domain()
        model._import_nlu_file()
        model._add_echo_conf()
        self.assertEqual(
            "AMAZON.NUMBER", model._slots_dir["num_people"]["type"])

    def test_intent_slots(self):
        model = echomodel.EchoModel("test", ".\\tests\\resources\\domain.yml",
                                    ".\\tests\\resources\\nlu.md",
                                    ".\\tests\\resources\\echo_domain.yml")
        model._import_domain()
        model._import_nlu_file()
        model._add_echo_conf()
        model._update_intent_slotlist()
        restaurant_intent = self.get_restaurant_intent(model)
        cuisine_slot = None
        for slot in restaurant_intent['slots']:
            if slot["name"] == "cuisine":
                cuisine_slot = slot
                break
        self.assertEqual("cuisine", cuisine_slot["type"])

    def test_entity_types(self):
        # check for example entry:
        # {
        #                     "name": {
        #                         "value": "gastropub",
        #                         "synonyms": [
        #                             "gastro pub"
        #                         ]
        #                     }
        #                 },
        model = echomodel.EchoModel("test", ".\\tests\\resources\\domain.yml",
                                    ".\\tests\\resources\\nlu.md",
                                    ".\\tests\\resources\\echo_domain.yml")
        model._import_domain()
        model._import_nlu_file()
        model._add_echo_conf()
        model._update_intent_slotlist()
        model._import_entity_definitions()
        types = model.model["interactionModel"]["languageModel"]["types"]

        gastropub_type = None
        for type_ in types:
            if type_["name"] == "cuisine":
                for value in type_["values"]:
                    if value["name"]["value"] == "gastropub":
                        gastropub_type = value
                        break
        print(gastropub_type)
        self.assertIn("gastro pub", gastropub_type["name"]["synonyms"])


if __name__ == '__main__':
    unittest.main()
