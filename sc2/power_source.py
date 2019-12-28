from .position import Point2


class PowerSource:
    @classmethod
    def from_proto(cls, proto):
        """ Get necessary info from sc2 protocol"""
        return cls(Point2.from_proto(proto.pos), proto.radius, proto.tag)

    def __init__(self, position, radius, unit_tag):
        if not isinstance(position, Point2):
            raise AssertionError()
        if radius <= 0:
            raise AssertionError()
        self.position = position
        self.radius = radius
        self.unit_tag = unit_tag

    def covers(self, position):
        return self.position.distance_to(position) <= self.radius

    def __repr__(self):
        return f"PowerSource({self.position}, {self.radius})"


class PsionicMatrix:
    @classmethod
    def from_proto(cls, proto):
        """ Get necessary info from sc2 protocol"""
        return cls([PowerSource.from_proto(p) for p in proto])

    def __init__(self, sources):
        self.sources = sources

    def covers(self, position):
        return any(source.covers(position) for source in self.sources)
