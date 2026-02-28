import sys
print("Python version:", sys.version)

from enum import Enum

class AppError(Enum):
    A = 1
    
    @property
    def value_str(self):
        return "str"

try:
    class AppError2(Enum):
        A = 1
        
        class Exception(Exception):
            pass

    print("AppError2.Exception:", AppError2.Exception)
    try:
        raise AppError2.Exception("test")
    except AppError2.Exception as e:
        print("Caught AppError2.Exception!", e)
except Exception as e:
    print("Failed with AppError2:", type(e), e)

try:
    class AppError3(Enum):
        _ignore_ = 'Exception'
        A = 1
        
        class Exception(Exception):
            pass

    print("AppError3.Exception:", AppError3.Exception)
    try:
        raise AppError3.Exception("test")
    except AppError3.Exception as e:
        print("Caught AppError3.Exception!", e)
except Exception as e:
    print("Failed with AppError3:", type(e), e)

try:
    class AppError4(Enum):
        A = 1
        
    class _Exception(Exception):
        pass
    AppError4.Exception = _Exception

    print("AppError4.Exception:", AppError4.Exception)
    try:
        raise AppError4.Exception("test")
    except AppError4.Exception as e:
        print("Caught AppError4.Exception!", e)
except Exception as e:
    print("Failed with AppError4:", type(e), e)
