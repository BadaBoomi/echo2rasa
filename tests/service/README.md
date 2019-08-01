Test the connector service with curl
    curl -XPOST http://localhost:5004/webhooks/echo/webhook -H "Content-type:application/json" -X POST -d @json.txt