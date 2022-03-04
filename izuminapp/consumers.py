import json
from channels.generic.websocket import WebsocketConsumer
from time import sleep



class WSConsumer(WebsocketConsumer) :
    def connect(self):
        self.accept()
        n = 0
        while True :
            n += 1
            self.send(json.dumps({"test" : "WStest : " + str(n)}))
            sleep(1)
