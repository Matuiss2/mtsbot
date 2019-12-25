"""Run the ladder or local game"""
import random

from bot_main import Mtsbot
from sc2 import maps
from sc2.main import run_game
from sc2.player import AIBuild, Bot, Computer, Difficulty, Race

if __name__ == "__main__":
    # Local game
    while True:
        # for security purposes, pointless in this scenario but do it anyway to get used to it
        SECURE_RANDOM = random.SystemRandom()
        MAP = SECURE_RANDOM.choice(
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
        BUILD = SECURE_RANDOM.choice([AIBuild.Macro, AIBuild.Rush, AIBuild.Timing, AIBuild.Power, AIBuild.Air])
        DIFFICULTY = SECURE_RANDOM.choice([Difficulty.VeryEasy, Difficulty.Easy])
        RACE = SECURE_RANDOM.choice([Race.Protoss, Race.Zerg, Race.Terran])
        """FINISHED_SETS = {
                BUILD == AIBuild.Macro and DIFFICULTY == Difficulty.CheatVision and RACE == Race.Zerg,
            }
            if any(FINISHED_SETS):
                print(f"{DIFFICULTY.name} {RACE.name} {BUILD.name} already done")
                continue"""
        break
    print(f"{DIFFICULTY.name} {RACE.name} {BUILD.name}")
    BOT = Bot(RACE.Zerg, Mtsbot())
    BUILTIN_BOT = Computer(RACE, DIFFICULTY, BUILD)
    run_game(maps.get(MAP), [BOT, BUILTIN_BOT], realtime=False)
