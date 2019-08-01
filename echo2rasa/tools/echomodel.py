""" Represents the RASA and Amazon Alexa needed NLU model configurations.

    Parameters
    ----------
    name : str
        invocation name of the Alexa/Echo skill.
    rasa_domain_file : file
        Location of the RASA domain file (i.e. domain.yml)
    rasa_nlu_file : file
        Location of the RASA NLU training file (i.e. nlu.md)
    echo_domain_file : file
        Location of the Alexa/Echo specific domain file (i.e. echo_domain.yml)

    Attributes
    ----------
    model : dictionary
        Alexa/Echo model representation. This will be exported as a json file.
"""

import re
import json
import yaml

# regular expression class variables used to parse configurations
re_entities_and_values = re.compile(r"(\[[^\[]*\][^\[]*\([^\[\(]*\))")
re_value = re.compile(r"(\[.*\])")
re_entity = re.compile(r"(\(.*\))")
re_is_key_value_pair = re.compile(r':.+')


class EchoModel(object):

    def __init__(
            self, name,
            rasa_domain_file, rasa_nlu_file,
            echo_domain_file):
        self._rasa_domain_file = rasa_domain_file
        self._rasa_nlu_file = rasa_nlu_file
        self._echo_domain_file = echo_domain_file
        self._intent_dir = {}    # Intents with their names and samples
        self._slots_dir = {}     # Slots with their names and types
        self._entitiy_types = {}  # Entity types and their values
        self.model = {
            "interactionModel": {
                "languageModel": {
                    "invocationName": name,
                    "intents": [],
                    "types": [],
                }
            }
        }

    def _import_domain(self):
        # Parse intents section of yaml file.
        # Every intent will be put into json representation
        # and added to the model.
        with open(self._rasa_domain_file, 'r') as stream:
            yml = yaml.safe_load(stream)
            intents = yml['intents']
            for intent in intents:
                if isinstance(intent, dict):
                    intentName = next(iter(intent))
                else:
                    intentName = intent
                self._intent_dir[intentName] = {
                    "name": intentName,
                    "samples": []
                }
                self.model['interactionModel']['languageModel']['intents']\
                    .append(self._intent_dir[intentName])

    def _update_intent_slotlist(self):

        def genSlots(slotList):
            resList = []
            for slot in slotList:
                resList.append(self._slots_dir[slot[1:-1]])
            return resList

        for intent in \
                self.model['interactionModel']['languageModel']['intents']:
            if ('slots' in intent):
                intentSlots = genSlots(list(set(intent['slots'])))
                intent['slots'] = intentSlots

    def _import_nlu_file(self):
        # Parse the nlu.md file and add utterances to corresponding intents
        # within our model
        def parse_utterance(utterance):
            # Remove quotation marks, commas and exclamation marks.
            # Remove sample values.
            # Remove numbers (digits)
            # Format for Alexa/Echo.
            def format_entities(matchobj):
                # Remove any entity value and replace parantheses with braces.

                # Example:
                #   matchobj: (entity:3)
                #   returns: {entity}

                entity_without_paranthesis = matchobj.group(0)[1:-1]
                idxOfCol = entity_without_paranthesis.find(':')
                if (idxOfCol >= 0):
                    entity_without_paranthesis = \
                        entity_without_paranthesis[0:idxOfCol]
                return "{"+entity_without_paranthesis+"}"

            # Remove "!". "," , "?" and digits.
            utterance = re.sub(r"(\?)", '', utterance)
            utterance = re.sub(r"(!)", '', utterance)
            utterance = re.sub(r"(,)", '', utterance)
            utterance = re.sub(r"(\d)", '', utterance)
            result = re.sub(r"(\(.*?\))", format_entities, utterance)

            # Remove example values
            # (i.e. replace [indonesian]{cuisine} by {cuisine})
            result = re.sub(r"(\[.*?\])", '', result)
            slots = re.findall(r"(\{.*?\})", result)
            return slots, result

        with open(self._rasa_nlu_file, 'r') as reader:
            line = reader.readline().strip()
            while line != '':  # The EOF char is an empty string
                # print(line, end='')
                if line.startswith('## intent:'):
                    # read utterances
                    intentName = line[10:]
                    intentSlots = []
                    line = reader.readline().strip()
                    while line.startswith('-'):
                        utterance = line[1:].strip()
                        # print('before:' + utterance)
                        slots, utterance = parse_utterance(utterance)
                        # print('after:' + utterance)
                        self._intent_dir[intentName]['samples'].append(
                            utterance)
                        if (len(slots) > 0):
                            intentSlots.extend(slots)
                        line = reader.readline().strip()
                    if (len(intentSlots) > 0):
                        self._intent_dir[intentName]['slots'] = intentSlots
                line = reader.readline().strip()

    def _import_entity_definitions(self):
        def update_entity(name, value, alias):
            entityName = self._slots_dir[name]["type"]
            entityEntry = self._entitiy_types.get(
                entityName, {value: []})
            entityValues = entityEntry.get(value, [])
            if (alias is not None):
                entityValues.append(alias)
            entityEntry[value] = list(set(entityValues))
            self._entitiy_types[entityName] = entityEntry

        entityAndValueList = []
        with open(self._rasa_nlu_file, 'r') as reader:
            for line in reader:
                entityAndValueList.extend(re_entities_and_values.findall(line))

        for entityAndValue in entityAndValueList:
            entityName = None
            entityValue = None

            entityEntry = {}
            hasAlias = False

            entityGroup = re_entity.search(entityAndValue)
            # i.e. [pan asian](cuisine:asian)
            if (entityGroup is not None):
                entityName = entityGroup[0][1: -1]  # i.e. cuisine:asian
                if (entityName.find(":") > 0):
                    entityName, entityValue = entityName.split(
                        ":")  # cuisine, asian
                    hasAlias = True

                valueGroup = re_value.search(entityAndValue)
                if (valueGroup is not None):
                    alias = valueGroup[0][1: -1]
                    if (hasAlias):
                        update_entity(entityName, entityValue, alias)
                    else:
                        update_entity(entityName, alias, None)

        types = []
        for type, typeValues in self._entitiy_types.items():
            # skip Alexa/Echo build in types
            if type.startswith("AMAZON"):
                continue
            values = []
            for value, aliases in typeValues.items():
                synonyms = []
                for alias in aliases:
                    synonyms.append(alias)
                if (len(synonyms) > 0):
                    values.append({
                        "name": {
                            "value": value,
                            "synonyms": synonyms
                        }
                    })
                else:
                    values.append({
                        "name": {
                            "value": value,
                        }
                    })
            types.append({"name": type,
                          "values": values, })
        self.model['interactionModel']['languageModel']['types'] = types

    def _add_echo_conf(self):
        with open(self._echo_domain_file, 'r') as stream:
            yml = yaml.safe_load(stream)
            slots = yml['slots']
            for name, typeDir in slots.items():
                self._slots_dir[name] = {'name': name, 'type': typeDir['type']}

    def export2echo(self, outFile):
        self._import_domain()
        self._import_nlu_file()
        self._add_echo_conf()
        self._update_intent_slotlist()
        self._import_entity_definitions()
        js = json.dumps(self.model)
        f = open(outFile, "w")
        f.write(js)
        f.close()
