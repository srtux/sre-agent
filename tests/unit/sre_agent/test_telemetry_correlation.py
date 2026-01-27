import json
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry import trace

from sre_agent.auth import SESSION_STATE_TRACE_ID_KEY, get_trace_id, set_trace_id
from sre_agent.core.runner_adapter import RunnerAgentAdapter
from sre_agent.services.agent_engine_client import AgentEngineClient, AgentEngineConfig


@pytest.fixture(scope="module", autouse=True)
def init_otel():
    """Initialize OTel for tests to ensure valid Trace IDs."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace import set_tracer_provider

    provider = TracerProvider()
    set_tracer_provider(provider)
    yield


@pytest.mark.asyncio
async def test_trace_id_propagation_flow():
    """Test that trace ID flows from client to session state and back in adapter."""
    from unittest.mock import AsyncMock

    # Ensure we use a real provider for valid IDs
    tracer = trace.get_tracer(__name__)

    # Mocking the session service
    mock_session = MagicMock()
    mock_session.id = "test-session"
    mock_session.state = {}

    mock_session_manager = MagicMock()
    mock_session_manager.get_or_create_session = AsyncMock(return_value=mock_session)
    mock_session_manager.update_session_state = AsyncMock()

    # 2. Setup Client
    config = AgentEngineConfig(project_id="p", location="l", agent_id="a")
    client = AgentEngineClient(config)
    client._initialized = True

    # Mock the ADK app's stream query
    mock_adk_app = MagicMock()

    async def mock_gen(*args, **kwargs):
        yield {"type": "event", "content": "hello"}

    mock_adk_app.async_stream_query = MagicMock(side_effect=mock_gen)
    client._adk_app = mock_adk_app

    # Run client.stream_query inside a span
    with tracer.start_as_current_span("parent-span") as span:
        trace_id_hex = format(span.get_span_context().trace_id, "032x")
        # print(f"DEBUG: Active Trace ID: {trace_id_hex}")

        with patch(
            "sre_agent.services.session.get_session_service",
            return_value=mock_session_manager,
        ):
            gen = client.stream_query(user_id="u", message="m", session_id="s")
            async for _ in gen:
                pass

    # Verify Client injected trace ID into session state delta
    update_calls = mock_session_manager.update_session_state.call_args_list
    assert len(update_calls) > 0, "update_session_state was not called"
    state_delta = update_calls[0][0][1]
    assert state_delta[SESSION_STATE_TRACE_ID_KEY] == trace_id_hex

    # 3. Setup RunnerAdapter to receive this session
    mock_runner = MagicMock()

    async def mock_runner_gen(*args, **kwargs):
        yield {"type": "event", "content": "from-runner"}

    mock_runner.run_turn.side_effect = mock_runner_gen

    adapter = RunnerAgentAdapter(mock_runner)

    # Mock context
    from google.adk.agents.invocation_context import InvocationContext

    mock_context = MagicMock(spec=InvocationContext)
    mock_context.session = mock_session
    mock_context.user_content = None
    mock_session.state[SESSION_STATE_TRACE_ID_KEY] = trace_id_hex

    # Reset manual trace ID context before running adapter
    set_trace_id(None)

    # Run adapter.run_async
    async for _ in adapter.run_async(mock_context):
        break

    # Verify Adapter extracted trace ID and set it in context
    assert get_trace_id() == trace_id_hex


def test_json_formatter_correlation():
    """Test that JsonFormatter includes trace IDs in the expected format."""
    import io
    import logging

    # Setup a logger with JSON format
    log_capture = io.StringIO()

    logger = logging.getLogger("test_json")
    logger.setLevel(logging.INFO)

    with patch.dict(
        "os.environ", {"LOG_FORMAT": "JSON", "GOOGLE_CLOUD_PROJECT": "test-proj"}
    ):
        with patch("sys.stderr", log_capture):
            from sre_agent.tools.common.telemetry import _configure_logging_handlers

            root_logger = logging.getLogger()
            for h in root_logger.handlers[:]:
                root_logger.removeHandler(h)

            _configure_logging_handlers(logging.INFO, "test-proj")

            # Case 1: Manual Trace ID (simulated fallback)
            set_trace_id("manual-trace-id")
            logger.info("Test message")

            output_str = log_capture.getvalue().strip()
            output = output_str.splitlines()
            assert len(output) > 0
            log_data = json.loads(output[-1])

            assert log_data["trace_id"] == "manual-trace-id"
            assert (
                log_data["logging.googleapis.com/trace"]
                == "projects/test-proj/traces/manual-trace-id"
            )

            # Case 2: OTel Trace ID (should be overridden by manual if manual is set)
            from opentelemetry import trace

            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span("test-span") as span:
                # In our new logic, if manual_trace_id is set, it WINS
                logger.warning("Warning message")

            # Read all logs emitted to stderr
            all_output = log_capture.getvalue().strip().splitlines()
            # Filter out empty lines and parse only the last one
            valid_logs = [line for line in all_output if line.strip()]
            assert len(valid_logs) > 0
            log_data = json.loads(valid_logs[-1])

            # Our current telemetry.py priority is manual > spans
            assert log_data["trace_id"] == "manual-trace-id"

            # Case 3: OTel Trace ID only (no manual)
            set_trace_id(None)
            with tracer.start_as_current_span("test-span-2") as span:
                otel_trace_id = format(span.get_span_context().trace_id, "032x")
                logger.error("Error message")

            all_output = log_capture.getvalue().strip().splitlines()
            valid_logs = [line for line in all_output if line.strip()]
            log_data = json.loads(valid_logs[-1])
            assert log_data["trace_id"] == otel_trace_id
            assert (
                log_data["logging.googleapis.com/trace"]
                == f"projects/test-proj/traces/{otel_trace_id}"
            )
