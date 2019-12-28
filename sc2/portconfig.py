"""
Connect and send it's configurations to unused ports
changed last: 28/12/2019
"""
import json

import portpicker


class Portconfig:
    "" "Connect, 'talk' and send the configurations to unused ports """
    def __init__(self):
        self.shared = portpicker.pick_unused_port()
        self.server = [portpicker.pick_unused_port() for _ in range(2)]
        self.players = [[portpicker.pick_unused_port() for _ in range(2)] for _ in range(2)]

    def __str__(self):
        return f"Portconfig(shared={self.shared}, server={self.server}, players={self.players})"

    @property
    def as_json(self):
        """ Serialize the info in JSON format"""
        return json.dumps({"shared": self.shared, "server": self.server, "players": self.players})

    @classmethod
    def from_json(cls, json_data):
        """ Deserialize the json data it's the inverse of the above function"""
        self = cls.__new__(cls)
        data = json.loads(json_data)
        self.shared = data["shared"]
        self.server = data["server"]
        self.players = data["players"]
        return self
