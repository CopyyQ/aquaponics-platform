class DomainError(Exception):
    """Base error for expected business-rule failures."""


class ResourceNotFoundError(DomainError):
    pass


class ProjectAccessDeniedError(DomainError):
    pass


class ResourceDisabledError(DomainError):
    pass


class InvalidLifecycleTransitionError(DomainError):
    pass
