from .ctx import Ctx, StopWalk
from .intent import Del, Get, Intent, Set


class State():
    def compile_check(self, 
                      path: list[str | int], 
                      pos: int, 
                      intent: type[Intent]):
        return False

    def run_check(self, ctx: Ctx):
        return False

    def __call__(self, ctx: Ctx):
        return

    def priority(self, path: list[str | int], pos: int, intent: type[Intent]):
        return 10

    @property
    def wildcard(self):
        return False

    def add_layer(self, ctx: Ctx):
        if isinstance(ctx.data, dict):
            if ctx.is_key(ctx.nkey):
                ctx.data[ctx.key] = {}
            else:
                ctx.data[ctx.key] = []
        elif isinstance(ctx.data, list):
            if ctx.is_key(ctx.nkey):
                ctx.data.append({})
            else:
                ctx.data.append([])

    def next_step(self, ctx: Ctx):
        if (
                (ctx.key in ctx.data) 
                or (not ctx.is_key(ctx.key) 
                    and ctx.key <= len(ctx.data)
                    and len(ctx.data) > 0)
            ):
            ctx.data = ctx.data[ctx.key]
        elif ctx.last_pos:
            return
        else:
            self.add_layer(ctx)
            ctx.data = ctx.data[ctx.key]


class KeyAccess(State):
    def compile_check(self, path, pos, intent):
        key = path[pos]
        return (
            isinstance(key, str) 
            and key not in {'*', '!a'}
        )

    def run_check(self, ctx):
        return ctx.key in ctx.data

    def __call__(self, ctx):
        self.next_step(ctx)
        if ctx.last_pos:
            ctx.result.append(ctx.data)


class KeySetAccess(KeyAccess):
    def run_check(self, ctx: Ctx):
        return (
            ctx.key not in ctx.data
            or (ctx.intent == Set and ctx.key not in ctx.data)
            or (ctx.intent == Set and ctx.last_pos)
        )

    def __call__(self, ctx: Ctx):
        if isinstance(ctx.data, dict):
            if ctx.last_pos:
                ctx.data[ctx.key] = ctx.value
                ctx.result.append(ctx.data[ctx.key])
            elif ctx.intent == Set:
                self.add_layer(ctx)
            else:
                raise StopWalk()
        elif isinstance(ctx.data, list):
            if ctx.last_pos:
                ctx.data.append(ctx.value)
            else:
                self.add_layer(ctx)
        self.next_step(ctx)

    def priority(self, path, pos, intent):
        if intent == Set:
            return 0
        else:
            return super().priority(path, pos, intent)


class DelState(State):
    def compile_check(self, path, pos, intent):
        return intent == Del

    def run_check(self, ctx):
        return ctx.last_pos

    def __call__(self, ctx):
        try:
            ctx.data.pop(ctx.key)
        except KeyError:
            raise StopWalk('Key not found')

    def priority(self, path, pos, intent):
        return 0


class IndexAccess(KeyAccess):
    def compile_check(self, path, pos, intent):
        key = path[pos]
        return (
            isinstance(key, int)
        )

    def run_check(self, ctx: Ctx):
        return (
            ctx.key < len(ctx.data)
            or ctx.key == -1
        )


class ListAppend(State):
    def compile_check(self, path, pos, intent):
        key = path[pos]
        return (
            key == '!a'
            and issubclass(intent, Set)
        )

    def priority(self, path, pos, intent):
        if intent == Set:
            return 0
        else:
            return super().priority(path, pos, intent)

    def run_check(self, ctx):
        return True

    def __call__(self, ctx):
        if isinstance(ctx.data, list):
            if ctx.last_pos:
                ctx.data.append(ctx.value)
            else:
                self.add_layer(ctx)
        else:
            raise NotImplementedError()
        self.next_step(ctx)


class IndexSet(IndexAccess):
    def compile_check(self, path, pos, intent):
        return isinstance(path[pos], int) and intent == Set 

    def run_check(self, ctx):
        return (
            not ctx.is_key(ctx.key) and (ctx.key >= len(ctx.data)
            or (ctx.key == -1 and ctx.last_pos)
            # or (ctx.intent == Set and ctx.key not in ctx.data)
            or (ctx.intent == Set and ctx.last_pos))
        )

    def priority(self, path, pos, intent):
        return 0

    def __call__(self, ctx: Ctx):
        if 0 < ctx.key < len(ctx.data):
            ctx.data[ctx.key] = ctx.value
        else:
            ctx.data.append(ctx.value)
        self.next_step(ctx)


class WildcardState(State):
    def compile_check(self, path, pos, intent):
        key = path[pos]
        return (
            key == '*'
        )

    def run_check(self, ctx):
        return True

    @property
    def wildcard(self):
        return True


class WGet(WildcardState):
    def compile_check(self, path, pos, intent):
        return (
            super().compile_check(path, pos, intent)
            and issubclass(intent, Get)
        )

    def __call__(self, ctx):
        for item in ctx.data:
            ctx.result.append(item)


class WDel(WildcardState):
    def compile_check(self, path, pos, intent):
        return (
            super().compile_check(path, pos, intent)
            and issubclass(intent, Del)
        )

    def __call__(self, ctx):
        ctx.data.clear()


class WSet(WildcardState):
    def compile_check(self, path, pos, intent):
        return (
            super().compile_check(path, pos, intent)
            and issubclass(intent, Set)
        )
    
    def __call__(self, ctx):
        for i in range(len(ctx.data)):
            ctx.data[i] = ctx.value