# The Elm Architecture in Espresso

Espresso applications follow the three principles of The Elm Architecture:

1. **Model**: Defines the state of your application.
2. **Update**: A pure function `update(msg)` that transitions your model based on an event.
3. **View**: A pure function `view()` that renders your model into a formatted string.

## Eliminating Race Conditions with `Cmd`

When you need to perform I/O (such as HTTP requests, timers, or disk access), do not block `update()`. Instead, return a `Cmd`:

```python
def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
    match msg:
        case KeyMsg(key="enter"):
            return self, self.fetch_data_cmd()
        case DataReceivedMsg(data=payload):
            self.data = payload
            return self, None
    return self, None
```

The runtime will execute the command asynchronously in the background and inject `DataReceivedMsg` back into `update()` sequentially, ensuring 100% determinism.
