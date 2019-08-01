REM curl -XPOST http://localhost:5005/webhooks/echo/webhook -H "Content-type:application/json" -X POST -d @json.txt
curl -XPOST http://localhost:5005/webhooks/echo/webhook -H "Content-type:application/json" -X POST -d @..\resources\echorequest.json
REM curl -XPOST https://64332fd1.ngrok.io/webhooks/echo/webhook -H "Content-type:application/json" -X POST -d @json.txt
