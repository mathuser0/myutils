from contextlib import contextmanager
import os
import tempfile

# You can import and rename things to work with them internally,
# without exposing them publicly or to avoid naming conflicts!
from atomicwrites import atomic_write as _backend_writer, AtomicWriter
import io as io2
import pandas as pd
from csci_utils.hash_str import get_csci_salt, get_user_id, hash_str

# You probably need to inspect and override some internals of the package
class SuffixWriter(AtomicWriter):
    def get_fileobject(self, dir=None, **kwargs):
        """Return the temporary file to use."""
        if dir is None:
            dir = os.path.normpath(os.path.dirname(self._path))
        descriptor, name = tempfile.mkstemp(
            suffix=os.path.splitext(self._path)[-1], prefix="tmp", dir=dir
        )
        # io.open() will take either the descriptor or the name, but we need
        # the name later for commit()/replace_atomic() and couldn't find a way
        # to get the filename from the descriptor.
        os.close(descriptor)
        kwargs["mode"] = self._mode
        kwargs["file"] = name
        return io2.open(**kwargs)

    @contextmanager
    def _open(self, get_fileobject):
        f = None  # make sure f exists even if get_fileobject() fails
        try:
            success = False
            with get_fileobject(**self._open_kwargs) as f:
                yield f
                self.sync(f)
            self.commit(f)
            success = True
        finally:
            if not success:
                try:
                    self.rollback(f)
                except Exception:
                    pass


@contextmanager
def atomic_write(file, mode="w", as_file=True, new_default="asdf", **kwargs):

    # You can override things just fine...
    with _backend_writer(file, writer_cls=SuffixWriter, **kwargs) as f:
        # Don't forget to handle the as_file logic!
        # try:
        # if as_file flag is True, yield the temporary file
        if as_file:
            yield f
        else:  # otherwise return the temporary file path string
            yield f.name
        # yield f


def get_user_hash(username, salt=None):
    """Converts username string to hash digest

    :param username: string to hash
    :param salt: add randomness to the hashing
    :return: hash digest of input
    """
    # get salt if provided else retrieve it from environment variables
    salt = salt or get_csci_salt()
    return hash_str(username, salt=salt)


def convert_excel_to_parquet(data_source):
    """Converts an excel file to an equivalent parquet file that gets saved

    :param data_source: path to input excel file
    :return: the path to the newly created parquet file
    """
    # read excel file
    df = pd.read_excel(data_source, index_col=0)

    # save dataframe to parquet file
    parquet_file = os.path.splitext(data_source)[0] + ".parquet"
    with atomic_write(parquet_file, as_file=False) as f:
        df.to_parquet(f, engine="pyarrow")

    # return parquet file path
    return parquet_file


def read_parquet_columns(parquet_file, columns):
    """Converts an excel file to an equivalent parquet file that gets saved

    :param parquet_file: path to parquet file
    :param columns: list of columns
    :return: dataframe containing requested columns only
    """
    # read only specified columns and return them
    data = pd.read_parquet(parquet_file, engine="pyarrow", columns=columns)
    return data
