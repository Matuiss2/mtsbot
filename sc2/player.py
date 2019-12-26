from .bot_ai import BotAI
from .data import AIBuild, Difficulty, PlayerType, Race


class AbstractPlayer:
    def __init__(self, p_type, race=None, name=None, difficulty=None, ai_build=None, fullscreen=False):
        if not isinstance(p_type, PlayerType):
            raise AssertionError(f"p_type is of type {type(p_type)}")
        if not (name is None or isinstance(name, str)):
            raise AssertionError(f"name is of type {type(name)}")

        self.name = name
        self.type = p_type
        self.fullscreen = fullscreen
        if race is not None:
            self.race = race
        if p_type == PlayerType.Computer:
            if not isinstance(difficulty, Difficulty):
                raise AssertionError(f"difficulty is of type {type(difficulty)}")
            # Workaround, proto information does not carry ai_build info
            # We cant set that in the Player classmethod
            if not (ai_build is None or isinstance(ai_build, AIBuild)):
                raise AssertionError(f"ai_build is of type {type(ai_build)}")
            self.difficulty = difficulty
            self.ai_build = ai_build

        elif p_type == PlayerType.Observer:
            if race is not None:
                raise AssertionError()
            if difficulty is not None:
                raise AssertionError()
            if ai_build is not None:
                raise AssertionError()

        else:
            if not isinstance(race, Race):
                raise AssertionError(f"race is of type {type(race)}")
            if difficulty is not None:
                raise AssertionError()
            if ai_build is not None:
                raise AssertionError()


# noinspection PyProtectedMember
class Human(AbstractPlayer):
    def __init__(self, race, name=None, fullscreen=False):
        super().__init__(PlayerType.Participant, race, name=name, fullscreen=fullscreen)

    def __str__(self):
        if self.name is not None:
            return f"Human({self.race._name_}, name={self.name !r})"
        return f"Human({self.race._name_})"


# noinspection PyProtectedMember
class Bot(AbstractPlayer):
    def __init__(self, race, ai, name=None, fullscreen=False):
        """
        AI can be None if this player object is just used to inform the
        server about player types.
        """
        if not (isinstance(ai, BotAI) or ai is None):
            raise AssertionError(f"ai is of type {type(ai)}, inherit BotAI from bot_ai.py")
        super().__init__(PlayerType.Participant, race, name=name, fullscreen=fullscreen)
        self.ai = ai

    # noinspection PyProtectedMember
    def __str__(self):
        if self.name is not None:
            return f"Bot {self.ai.__class__.__name__}({self.race._name_}), name={self.name !r})"
        return f"Bot {self.ai.__class__.__name__}({self.race._name_})"


class Computer(AbstractPlayer):
    def __init__(self, race, difficulty=Difficulty.Easy, ai_build=AIBuild.RandomBuild):
        super().__init__(PlayerType.Computer, race, difficulty=difficulty, ai_build=ai_build)

    def __str__(self):
        # noinspection PyProtectedMember,PyProtectedMember
        return f"Computer {self.difficulty._name_}({self.race._name_}, {self.ai_build.name})"


class Observer(AbstractPlayer):
    def __init__(self):
        super().__init__(PlayerType.Observer)

    def __str__(self):
        return f"Observer"


class Player(AbstractPlayer):
    @classmethod
    def from_proto(cls, proto):
        if PlayerType(proto.type) == PlayerType.Observer:
            return cls(proto.player_id, PlayerType(proto.type), None, None, None)
        return cls(
            proto.player_id,
            PlayerType(proto.type),
            Race(proto.race_requested),
            Difficulty(proto.difficulty) if proto.HasField("difficulty") else None,
            Race(proto.race_actual) if proto.HasField("race_actual") else None,
            proto.player_name if proto.HasField("player_name") else None,
        )

    def __init__(self, player_id, p_type, requested_race, difficulty=None, actual_race=None, name=None, ai_build=None):
        super().__init__(p_type, requested_race, difficulty=difficulty, name=name, ai_build=ai_build)
        self.id: int = player_id
        self.actual_race: Race = actual_race
