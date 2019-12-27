"""Run the ladder or local game"""
import random

from bot_main import Mtsbot
from sc2 import maps
from sc2.main import run_game
from sc2.player import AI_BUILD, Bot, Computer, DIFFICULTY, RACE

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
        BUILD = SECURE_RANDOM.choice([AI_BUILD.Macro, AI_BUILD.Rush, AI_BUILD.Timing, AI_BUILD.Power, AI_BUILD.Air])
        DIFFICULTY = SECURE_RANDOM.choice([DIFFICULTY.VeryEasy, DIFFICULTY.Easy])
        RACE = SECURE_RANDOM.choice([RACE.Protoss, RACE.Zerg, RACE.Terran])
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
