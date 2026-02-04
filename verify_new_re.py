import vertexai
from vertexai import agent_engines

PROJECT_ID = "summitt-gcp"
LOCATION = "us-central1"
RESOURCE_ID = "4160062716830023680"


def verify():
    """Verify the reasoning engine."""
    print(f"Verifying RE {RESOURCE_ID}...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    try:
        eng = agent_engines.get(RESOURCE_ID)
        print(f"Found: {eng.resource_name}")
        print(f"Display Name: {eng.display_name}")

        # Check identity
        if hasattr(eng, "_gca_resource"):
            proto = eng._gca_resource
            # Check identity_config
            if hasattr(proto, "identity_config"):
                print(f"Identity Config: {proto.identity_config}")
            else:
                print("Identity Config: Not Found (None)")

            # Check service_account
            print(f"Service Account field: {getattr(proto, 'service_account', 'N/A')}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    verify()
