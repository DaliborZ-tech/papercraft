"""Rollback boundary shared by independent command families."""

import copy
from functools import wraps

from .errors import ValidationError


def atomic(method):
    @wraps(method)
    def command(self, *args, **kwargs):
        before = copy.deepcopy(self.__dict__)
        try:
            result = method(self, *args, **kwargs)
            self.validate()
            return result
        except Exception as exc:
            self.__dict__.clear()
            self.__dict__.update(before)
            if isinstance(
                exc, (KeyError, TypeError, ValueError, AttributeError, IndexError, OverflowError)
            ) and not isinstance(exc, ValidationError):
                raise ValidationError(f"Operaci nelze provést: {exc}") from exc
            raise

    return command
