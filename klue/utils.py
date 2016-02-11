from importlib import import_module
from klue.exceptions import KlueException

def get_function(pkgpath):
    """Take a full path to a python method, for example mypkg.subpkg.method and
    return the method (after importing the required packages)
    """
    # Extract the module and function name from pkgpath
    elems = pkgpath.split('.')
    if len(elems) <= 1:
        raise KlueException("Path %s is too short. Should be at least module.func." % elems)
    func_name = elems[-1]
    func_module = '.'.join(elems[0:-1])

    # Load the function's module and get the function
    try:
        m = import_module(func_module)
        f = getattr(m, func_name)
        return f
    except Exception as e:
        raise KlueException("Failed to import %s: " % pkgpath + str(e))
