import copy
import operator


empty: object = object()


def unpickle_lazyobject(wrapped: object) -> object:
    """
    Used to unpickle lazy objects. Just return its argument, which will be the
    wrapped object.

    Parameters:
        wrapped: The wrapped object.

    Returns:
        The wrapped object.
    """
    return wrapped


def new_method_proxy(func: callable) -> callable:
    """
    Create a method proxy for the given function.

    Parameters:
        func: The function to create a method proxy for.

    Returns:
        A method proxy for the given function.
    """

    def inner(self, *args: tuple) -> object:
        """
        The method proxy.

        Parameters:
            self: The object to proxy the method for.
            *args: The arguments to pass to the function.

        Returns:
            The result of the function.
        """
        if self._wrapped is empty:
            self._setup()
        return func(self._wrapped, *args)

    return inner


class LazyObject:
    """
    A wrapper for another class that can be used to delay instantiation of the
    wrapped class.
    By subclassing, you have the opportunity to intercept and alter the
    instantiation.
    """

    # Avoid infinite recursion when tracing __init__ (#19456).
    _wrapped = None

    def __init__(self) -> None:
        """
        Initialize the wrapped object.

        Parameters:
            None.

        Returns:
            None.
        """
        # Note: if a subclass overrides __init__(), it will likely need to
        # override __copy__() and __deepcopy__() as well.
        self._wrapped: object = empty

    __getattr__ = new_method_proxy(getattr)

    def __setattr__(self, name: str, value: object) -> None:
        """
        Set an attribute on the wrapped object.

        Parameters:
            name: The name of the attribute to set.
            value: The value to set the attribute to.

        Returns:
            None.
        """
        if name == "_wrapped":
            # Assign to __dict__ to avoid infinite __setattr__ loops.
            self.__dict__["_wrapped"] = value
        else:
            if self._wrapped is empty:
                self._setup()
            setattr(self._wrapped, name, value)

    def __delattr__(self, name: str) -> None:
        """
        Delete an attribute on the wrapped object.

        Parameters:
            name: The name of the attribute to delete.

        Returns:
            None.

        Raises:
            TypeError: If the attribute to delete is _wrapped.
        """

        if name == "_wrapped":
            raise TypeError("can't delete _wrapped.")
        if self._wrapped is empty:
            self._setup()
        delattr(self._wrapped, name)

    def _setup(self) -> None:
        """
        Must be implemented by subclasses to initialize the wrapped object.

        Parameters:
            None.

        Returns:
            None.

        Raises:
            NotImplementedError: If not implemented by a subclass.
        """
        raise NotImplementedError(
            "subclasses of LazyObject must provide a _setup() method"
        )

    # Because we have messed with __class__ below, we confuse pickle as to what
    # class we are pickling. We're going to have to initialize the wrapped
    # object to successfully pickle it, so we might as well just pickle the
    # wrapped object since they're supposed to act the same way.
    #
    # Unfortunately, if we try to simply act like the wrapped object, the ruse
    # will break down when pickle gets our id(). Thus we end up with pickle
    # thinking, in effect, that we are a distinct object from the wrapped
    # object, but with the same __dict__. This can cause problems (see #25389).
    #
    # So instead, we define our own __reduce__ method and custom unpickler. We
    # pickle the wrapped object as the unpickler's argument, so that pickle
    # will pickle it normally, and then the unpickler simply returns its
    # argument.
    def __reduce__(self) -> tuple:
        """
        Reduce the wrapped object.

        Parameters:
            None.

        Returns:
            A tuple containing the unpickler and the wrapped object.
        """

        if self._wrapped is empty:
            self._setup()
        return (unpickle_lazyobject, (self._wrapped,))

    def __copy__(self) -> object:
        """
        Copy the wrapped object.

        Parameters:
            None.

        Returns:
            A copy of the wrapped object.
        """
        if self._wrapped is empty:
            # If uninitialized, copy the wrapper. Use type(self), not
            # self.__class__, because the latter is proxied.
            return type(self)()
        else:
            # If initialized, return a copy of the wrapped object.
            return copy.copy(self._wrapped)

    def __deepcopy__(self, memo: str) -> object:
        """
        Deep copy the wrapped object.

        Parameters:
            memo: The memo.

        Returns:
            A deep copy of the wrapped object.
        """
        if self._wrapped is empty:
            # We have to use type(self), not self.__class__, because the
            # latter is proxied.
            result = type(self)()
            memo[id(self)]: object = result
            return result
        return copy.deepcopy(self._wrapped, memo)

    __bytes__: bytes = new_method_proxy(bytes)
    __str__: str = new_method_proxy(str)
    __bool__: bool = new_method_proxy(bool)

    # Introspection support
    __dir__ = new_method_proxy(dir)

    # Need to pretend to be the wrapped class, for the sake of objects that
    # care about this (especially in equality tests)
    __class__ = property(new_method_proxy(operator.attrgetter("__class__")))
    __eq__ = new_method_proxy(operator.eq)
    __lt__ = new_method_proxy(operator.lt)
    __gt__ = new_method_proxy(operator.gt)
    __ne__ = new_method_proxy(operator.ne)
    __hash__ = new_method_proxy(hash)

    # List/Tuple/Dictionary methods support
    __getitem__ = new_method_proxy(operator.getitem)
    __setitem__ = new_method_proxy(operator.setitem)
    __delitem__ = new_method_proxy(operator.delitem)
    __iter__ = new_method_proxy(iter)
    __len__ = new_method_proxy(len)
    __contains__ = new_method_proxy(operator.contains)


class cached_property:
    """
    Decorator that converts a method with a single self argument into a
    property cached on the instance.

    A cached property can be made out of an existing method:
    (e.g. ``url = cached_property(get_absolute_url)``).
    The optional ``name`` argument is obsolete as of Python 3.6 and will be
    deprecated in Django 4.0 (#30127).
    """

    name = None

    @staticmethod
    def func(instance):
        raise TypeError(
            "Cannot use cached_property instance without calling "
            "__set_name__() on it."
        )

    def __init__(self, func, name=None):
        self.real_func = func
        self.__doc__ = getattr(func, "__doc__")

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name
            self.func = self.real_func
        elif name != self.name:
            raise TypeError(
                "Cannot assign the same cached_property to two different names "  # noqa: E501
                "(%r and %r)." % (self.name, name)
            )

    def __get__(self, instance, cls=None):
        """
        Call the function and put the return value in instance.__dict__ so that
        subsequent attribute access on the instance returns the cached value
        instead of calling cached_property.__get__().
        """
        if instance is None:
            return self
        res = instance.__dict__[self.name] = self.func(instance)
        return res
