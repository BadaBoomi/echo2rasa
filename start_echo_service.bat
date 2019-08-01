set PYTHONPATH=%CD%\echo2rasa
start "action-server" rasa run actions --actions actions
rasa run --connector echoconnector.EchoConnector --port 5005
