import pandas as pd
import os
import types

def cache(cache_path: str):
    def real_decorator(func: types.FunctionType):
        def decorator(*args, **kwargs):
            print(cache_path, os.path.exists(cache_path))
            if os.path.exists(cache_path):
                # assume the cached output is always saved as compressed pickle
                print("Loaded cache " + os.path.realpath(cache_path))
                return pd.read_pickle(cache_path)
            else:
                output = func(*args, **kwargs)
                print("Caching data to " + os.path.realpath(cache_path))
                output.to_pickle(cache_path, compression='gzip')
                return output

        return decorator
    return real_decorator
