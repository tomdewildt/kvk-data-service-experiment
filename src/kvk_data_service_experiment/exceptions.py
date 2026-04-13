class UnknownCommandError(Exception):
    def __init__(self, command: str):
        super().__init__(f"Unknown command: '{command}'")
        self.command = command
