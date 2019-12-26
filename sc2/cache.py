from functools import wraps


def property_cache_forever(function):
    @wraps(function)
    def inner(self):
        property_cache = "_cache_" + function.__name__
        cache_updated = hasattr(self, property_cache)
        if not cache_updated:
            setattr(self, property_cache, function(self))
        cache = getattr(self, property_cache)
        return cache

    return property(inner)


def property_cache_once_per_frame(function):
    """ This decorator caches the return value for one game loop,
    then clears it if it is accessed in a different game loop.
    Only works on properties of the bot object, because it requires
    access to self.state.game_loop """

    @wraps(function)
    def inner(self):
        property_cache = "_cache_" + function.__name__
        state_cache = "_frame_" + function.__name__
        cache_updated = getattr(self, state_cache, -1) == self.state.game_loop
        if not cache_updated:
            setattr(self, property_cache, function(self))
            setattr(self, state_cache, self.state.game_loop)

        cache = getattr(self, property_cache)
        should_copy = callable(getattr(cache, "copy", None))
        if should_copy:
            return cache.copy()
        return cache

    return property(inner)


def property_cache_once_per_frame_no_copy(function):
    """ This decorator caches the return value for one game loop,
    then clears it if it is accessed in a different game loop.
    Only works on properties of the bot object, because it requires
    access to self.state.game_loop

    This decorator compared to the above runs a little faster, however you should only use this decorator if you are
    sure that you do not modify the mutable once it is calculated and cached. """

    @wraps(function)
    def inner(self):
        property_cache = "_cache_" + function.__name__
        state_cache = "_frame_" + function.__name__
        cache_updated = getattr(self, state_cache, -1) == self.state.game_loop
        if not cache_updated:
            setattr(self, property_cache, function(self))
            setattr(self, state_cache, self.state.game_loop)

        cache = getattr(self, property_cache)
        return cache

    return property(inner)


def property_immutable_cache(function):
    """ This cache should only be used on properties that return an immutable object
    (bool, str, int, float, tuple, Unit, Point2, Point3) """

    @wraps(function)
    def inner(self):
        if function.__name__ not in self.cache:
            self.cache[function.__name__] = function(self)
        return self.cache[function.__name__]

    return property(inner)


def property_mutable_cache(function):
    """ This cache should only be used on properties that return a mutable object (Units, list, set, dict, Counter) """

    @wraps(function)
    def inner(self):
        if function.__name__ not in self.cache:
            self.cache[function.__name__] = function(self)
        return self.cache[function.__name__].copy()

    return property(inner)
