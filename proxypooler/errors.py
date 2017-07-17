
class ProxyPoolerError(Exception):
    """proxypooler base error"""


class ProxyPoolerEmptyError(ProxyPoolerError):
    """proxypooler empty error"""

class ProxyPoolerStoppedError(ProxyPoolerError):
    """proxypooler stopped error"""
