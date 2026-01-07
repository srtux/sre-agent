
import functools
import logging
import time
import inspect
from typing import Any, Callable

logger = logging.getLogger(__name__)

def adk_tool(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to mark a function as an ADK tool and provide automatic logging.
    
    This decorator logs:
    - Tool execution start with arguments
    - Tool execution success/failure with duration
    - Exceptions raised by the tool
    
    It preserves the original function signature and docstring.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tool_name = func.__name__
        
        # Format arguments for logging (truncate long values if needed)
        # We bind arguments to valid signature to get parameter names if possible
        try:
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            arg_str = ", ".join(f"{k}={repr(v)[:200]}" for k, v in bound.arguments.items())
        except Exception:
            # Fallback if signature binding fails or for some reason
            arg_str = f"args={args}, kwargs={kwargs}"
            
        logger.info(f"Tool '{tool_name}' called with: {arg_str}")
        
        start_time = time.time()
        try:
            # Check if the function is a coroutine
            if inspect.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
                
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"Tool '{tool_name}' completed in {duration_ms:.2f}ms")
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Tool '{tool_name}' failed after {duration_ms:.2f}ms: {e}", exc_info=True)
            raise e

    # If the function is NOT async, we should probably return a sync wrapper 
    # BUT LlmAgent might expect async? 
    # Actually, LlmAgent handles sync functions by wrapping them in runs_in_executor usually,
    # OR if we provide an async wrapper to a sync function, it works fine as long as the agent awaits it.
    # However, for 'adk_tool' which might be used in other contexts, strictly speaking we should 
    # match the sync/async nature or force async.
    # Given the previous context where we just returned 'func' (pass-through), 
    # the agent likely inspects the underlying function.
    # If we wrap it, we hide the original sync function behind an async wrapper if we are not careful.
    
    # ADK's FunctionTool.from_func inspects the function.
    # If using LlmAgent(tools=[func]), it inspects func.
    # If we wrap it, it inspects the wrapper.
    # If we make the wrapper async, LlmAgent sees an async tool.
    
    if inspect.iscoroutinefunction(func):
        return wrapper
    else:
        # Sync version for sync functions
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            tool_name = func.__name__
            try:
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                arg_str = ", ".join(f"{k}={repr(v)[:200]}" for k, v in bound.arguments.items())
            except Exception:
                arg_str = f"args={args}, kwargs={kwargs}"
            
            logger.info(f"Tool '{tool_name}' called with: {arg_str}")
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.info(f"Tool '{tool_name}' completed in {duration_ms:.2f}ms")
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f"Tool '{tool_name}' failed after {duration_ms:.2f}ms: {e}", exc_info=True)
                raise e
        return sync_wrapper

