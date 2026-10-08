"""Storage failures that are safe to handle above the driver.

Exception text from MongoDB or S3 can contain a connection string or an
account identifier. Callers log the exception type and return a fixed message.
"""


class RepositoryUnavailable(Exception):
    """The database could not complete an operation."""


class ObjectNotFoundError(Exception):
    """The object key is not in the bucket."""


class StorageError(Exception):
    """Object storage rejected or could not finish an operation."""
