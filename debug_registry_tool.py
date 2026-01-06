
import os
import asyncio
import google.auth
from google.adk.tools.api_registry import ApiRegistry

async def main():
    try:
        _, project_id = google.auth.default()
        project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        
        if not project_id:
            print("Error: No project ID found.")
            return

        print(f"Using Project ID: {project_id}")
        
        server_name = f"projects/{project_id}/locations/global/mcpServers/google-bigquery.googleapis.com-mcp"
        registry = ApiRegistry(project_id)
        
        print("Loading toolset...")
        bq_tools = registry.get_toolset(
            mcp_server_name=server_name,
            tool_filter=["execute_sql"]
        )
        
        print(f"Dir of tools: {dir(bq_tools)}")
        
        real_tools = await bq_tools.get_tools() # Await the coroutine
        print(f"Real tools type: {type(real_tools)}")
        if isinstance(real_tools, list):
            print(f"Count: {len(real_tools)}")
            for t in real_tools:
                print(f" - {t.name} ({type(t)})")
        elif isinstance(real_tools, dict):
            print(f"Count: {len(real_tools)}")
            real_tools = list(real_tools.values())
        
        # execution
        execute_sql_tool = None
        for t in real_tools:
            if t.name == "execute_sql":
                execute_sql_tool = t
                break
        
        if not execute_sql_tool:
             print("Error: execute_sql tool not found in get_tools() output.")
             return

        print("Executing query...")
        query = "SELECT 1 as test_col"
        try:
            if hasattr(execute_sql_tool, 'run_async'):
                print("Calling run_async with args kwarg and tool_context...")
                # Correct signature found via inspection: (*, args, tool_context)
                result = await execute_sql_tool.run_async(args={"projectId": project_id, "query": query}, tool_context=None)
            else:
                print(f"Tool has no run_async method. Dir: {dir(execute_sql_tool)}")
                return
            
            print(f"Execution Result type: {type(result)}")
            print(f"Execution Result: {result}")
            
            # Check if it's a coroutine
            if asyncio.iscoroutine(result):
                result = await result
                print(f"Awaited Result: {result}")
                
        except Exception as tool_exc:
            print(f"Tool execution failed: {tool_exc}")
            import traceback
            traceback.print_exc()




        # Second execution block removed as it was redundant and incorrect.
        print("Done.")

    except Exception as e:
        print(f"Top level error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
