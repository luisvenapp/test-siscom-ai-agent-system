import inspect
from functools import lru_cache
from inspect import Parameter
from typing import Any, Callable, Tuple


@lru_cache(maxsize=512)
def _get_func_parameters(
    func: Callable[..., Any],
    remove_first: bool,
) -> Tuple[Parameter, ...]:
    """
    Get the parameters of a function.

    Args:
        func: The target function object.
        remove_first: If True, drop the first parameter (e.g., 'self').

    Returns:
        A tuple of inspect.Parameter objects.
    """
    params = tuple(inspect.signature(func).parameters.values())
    if remove_first:
        params = params[1:]
    return params


def _get_callable_parameters(
    meth_or_func: Callable[..., Any],
) -> Tuple[Parameter, ...]:
    """
    Get parameters for a callable, removing 'self' for bound methods.

    Args:
        meth_or_func: A function or bound method.

    Returns:
        A tuple of inspect.Parameter objects.
    """
    is_method = inspect.ismethod(meth_or_func)
    # For bound methods, retrieve the underlying function
    func = meth_or_func.__func__ if is_method else meth_or_func  # type: ignore
    return _get_func_parameters(func, remove_first=is_method)


def method_has_no_args(meth: Callable[..., Any]) -> bool:
    """
    Determine if a method only accepts 'self', or a function only one arg.

    Args:
        meth: The method or function to inspect.

    Returns:
        True if:
          - A bound method has no parameters beyond 'self'.
          - A standalone function has exactly one positional or keyword arg.
    """
    params = _get_callable_parameters(meth)
    # Count only positional-or-keyword parameters
    count = sum(1 for p in params if p.kind == p.POSITIONAL_OR_KEYWORD)

    if inspect.ismethod(meth):
        return count == 0

    return count == 1
