import asyncio
import os
import sys

# Ensure project root is in path
sys.path.append(os.getcwd())

from sre_agent.services.session import get_session_service


async def reproduce():
    print("🚀 Starting reproduction script...")

    # 1. Initialize Service
    service = get_session_service()

    # 2. Create Sessions for User A and User B
    user_a = "user_a@example.com"
    user_b = "user_b@example.com"

    print(f"\nCreating session for {user_a}...")
    session_a = await service.create_session(
        user_id=user_a, initial_state={"title": "User A Session"}
    )
    print(f"✅ Created Session A: {session_a.id}")

    print(f"\nCreating session for {user_b}...")
    session_b = await service.create_session(
        user_id=user_b, initial_state={"title": "User B Session"}
    )
    print(f"✅ Created Session B: {session_b.id}")

    # 3. List Sessions for User A (Should only see Session A)
    print(f"\nListing sessions for {user_a}...")
    list_a = await service.list_sessions(user_id=user_a)
    ids_a = [s.id for s in list_a]
    print(f"Session IDs for A: {ids_a}")

    if session_a.id in ids_a and session_b.id not in ids_a:
        print("✅ User A sees their session and NOT User B's.")
    else:
        print("❌ User A sees incorrect sessions!")
        print(f"Expected: {[session_a.id]}")
        print(f"Actual: {ids_a}")

    # 4. List Sessions for Default User (Should see none or only default)
    print("\nListing sessions for 'default' user...")
    list_default = await service.list_sessions(user_id="default")
    ids_default = [s.id for s in list_default]
    print(f"Session IDs for Default: {ids_default}")

    # 5. Access Check: Can User A get User B's session?
    # Note: get_session usually allows retrieval by ID if backend doesn't strictly enforce ownership check in get_session itself
    # but list_sessions MUST filter.
    print(f"\nAttempting to get Session B ({session_b.id}) as {user_a}...")
    session_b_as_a = await service.get_session(session_id=session_b.id, user_id=user_a)
    if session_b_as_a:
        # This might be allowed depending on implementation, but strictly speaking should ideally be restricted or at least we know it works.
        # But if list_sessions works, that's the main "Previous Sessions" view.
        print(
            "⚠️ User A WAS able to retrieve Session B by ID directly. (This might be intentional for shared links, but checking behavior)"
        )
    else:
        print("✅ User A could NOT retrieve Session B.")

    # 6. Check what the frontend actually uses
    # The frontend uses list_sessions to populate the sidebar.

    print("\n🏁 Reproduction complete.")


if __name__ == "__main__":
    asyncio.run(reproduce())
