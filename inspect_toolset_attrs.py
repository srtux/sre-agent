
import inspect
from google.adk.tools.base_toolset import BaseToolset

print(f"BaseToolset dir: {dir(BaseToolset)}")
try:
    t = BaseToolset()
    print(f"BaseToolset instance dir: {dir(t)}")
except Exception as e:
    print(f"Could not instantiate BaseToolset: {e}")
