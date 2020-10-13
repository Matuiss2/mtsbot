"""  Run the ladder or local game"""
import random
import sys

from __init__ import run_ladder_game
from bot_main import Mtsbot
from sc2 import maps
from sc2.main import run_game
from sc2.player import AI_BUILD, DIFFICULTY, RACE, Bot, Computer

if __name__ == "__main__":
    BOT = Bot(RACE.Zerg, Mtsbot(), name="Mtsbot")
    if "--LadderServer" in sys.argv:
        # Ladder game started by LadderManager
        print("Starting ladder game...")
        run_ladder_game(BOT)
    else:
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
            DIFFICULTY = SECURE_RANDOM.choice(
                [
                    DIFFICULTY.VeryEasy,
                    DIFFICULTY.Easy,
                    DIFFICULTY.Medium,
                    DIFFICULTY.MediumHard,
                    DIFFICULTY.Hard,
                    DIFFICULTY.Harder,
                    DIFFICULTY.VeryHard,
                ]
            )
            RACE = SECURE_RANDOM.choice([RACE.Protoss, RACE.Terran, RACE.Zerg])
            """FINISHED_SETS = {
                DIFFICULTY != DIFFICULTY.VeryHard or RACE != RACE.Terran or BUILD != BUILD.Timing,
                }
                if any(FINISHED_SETS):
                    print(f"{DIFFICULTY.name} {RACE.name} {BUILD.name} already done")
                    continue"""
            break
        print(f"{DIFFICULTY.name} {RACE.name} {BUILD.name}")
        BUILTIN_BOT = Computer(RACE, DIFFICULTY, BUILD)
        run_game(maps.get(MAP), [BOT, BUILTIN_BOT], realtime=False)
