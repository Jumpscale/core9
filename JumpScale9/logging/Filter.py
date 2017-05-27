class ModuleFilter:
    """ModuleFilter filter out given modules"""

    def __init__(self, modules):
        """
        modules is an iterable containing the name of the modules to filter
        """
        self.modules = modules

    def filter(self, record):
        if record.name not in self.modules:
            return True
        return False
