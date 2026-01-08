
try:
    from google.cloud import errorreporting_v1beta1
    print("Import successful")
    print(errorreporting_v1beta1)
except ImportError as e:
    print(f"Import failed: {e}")

try:
    import google.cloud.error_reporting
    print("Top level import successful")
except ImportError as e:
    print(f"Top level import failed: {e}")
