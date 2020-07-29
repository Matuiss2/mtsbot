"""
Test if the bot hold simple worker rushes
"""

import random

from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.main import run_game
from sc2.player import Bot, RACE

from bot_main import Mtsbot


class WorkerRushBot(BotAI):
    """ Simplest worker rush bot possible"""

    async def on_step(self, iteration):
        if not iteration:
            for worker in self.workers:
                self.do(worker.attack(self.enemy_start_locations[0]))


secure_random = random.SystemRandom()
chosen_map = secure_random.choice(
    [
        "AcropolisLE",
        "DiscoBloodbathLE",
        "EphemeronLE",
        "ThunderbirdLE",
        "TritonLE",
        "WintersGateLE",
        "WorldofSleepersLE",
    ]
)
simple_worker_rush_bot = Bot(RACE.Random, WorkerRushBot(), name="Worker Rush")
mtsbot = Bot(RACE.Zerg, Mtsbot(), name="Mtsbot")
run_game(maps.get(chosen_map), [mtsbot, simple_worker_rush_bot], realtime=False)
