# microbit-mcp AI Coding Instructions

## Architecture Overview

This is an **MCP (Model Context Protocol) server** that bridges AI agents with physical micro:bit devices via serial communication. The system has three main layers:

- **MCP Server** (`src/mcp_server/`) - Exposes micro:bit capabilities as MCP tools for AI agents
- **Serial Protocol** - Custom command/response format for micro:bit communication  
- **micro:bit Firmware** (`src/microbit/main.py`) - MicroPython code flashed to the device

### Key Design Patterns

**Tool-Based Architecture**: Each micro:bit capability (display, sensors, input, music) is organized as an MCP tool in `src/mcp_server/tools/`. Tools follow a consistent pattern:
- `get_*_tools()` - Returns tool definitions with JSON schemas
- `handle_*_tool()` - Async handler that calls `MicrobitClient` methods

**Protocol Layer**: All serial communication goes through `protocol.py` which defines:
- Command formats: `MESSAGE:`, `IMAGE:`, `TEMP:`, `WAIT_BUTTON:`, `MUSIC:`
- Response parsing: `TEMP|data|timestamp`, `BUTTON|button|action|timestamp`
- Data sanitization (ASCII conversion, length limits)

## Development Workflows

### Running the Server
```bash
# Standard usage (auto-detects micro:bit port)
uv run microbit-mcp

# List available serial ports
uv run microbit-mcp --list-ports

# Specify custom port
uv run microbit-mcp -p /dev/ttyUSB0
```

### Debugging with MCP Inspector
Use `npx @modelcontextprotocol/inspector` with command: `/path/to/uv` and args: `--directory /full-path run microbit-mcp`

### micro:bit Setup
Flash `src/microbit/main.py` to your micro:bit - this is **required** as it implements the custom protocol, not standard MicroPython APIs. **Supports both micro:bit v1 and v2 boards** - firmware auto-detects version.

## Project-Specific Conventions

### Serial Communication Patterns
- **Commands are synchronous** - send command, micro:bit processes immediately
- **Responses are async** - temperature/button tools wait for specific response formats
- **Timeouts are crucial** - all micro:bit interactions have fallback timeouts (typically 5-10s)

### Tool Implementation Rules
1. **All tools return `list[types.TextContent]`** - JSON responses use `json.dumps()`
2. **Error handling at tool level** - validate inputs before sending to micro:bit
3. **Protocol commands must match firmware** - see `main.py` command parsing

### File Organization
- **New tools**: Add to `src/mcp_server/tools/` with separate files per category
- **Tool registration**: Update `tools/__init__.py` to include in `get_all_tools()`
- **Protocol changes**: Update both `protocol.py` and `src/microbit/main.py`

## Critical Integration Points

### MicrobitClient State Management
- Connection is **async singleton** - established once in `server.py:setup()`
- **Reader/writer streams** persist for entire session - don't recreate
- **Connection errors bubble up** - tools should handle `MicrobitClient` exceptions

### Button Press Workflow
The button system is **stateful on micro:bit side**:
1. Send `WAIT_BUTTON:button:timeout` 
2. micro:bit enters button monitoring mode
3. Waits for `BUTTON|button|pressed|timestamp` OR `BUTTON_TIMEOUT|waited_for|duration`
4. Python client has +1s timeout buffer over micro:bit timeout

### Example Command Flow
```python
# Tool call: wait_for_button_press(button="a", timeout=5.0)
await microbit_client.send_command("WAIT_BUTTON:a:5.0")
response = await microbit_client.read_button_response("a")  # Waits up to 6s
```

## Testing & Examples

### Agent Example
See `src/examples/basic/main.py` - uses OpenAI Agents with Gradio UI. Shows proper MCP server initialization and streaming responses.

### Port Detection
`list_serial_ports()` in `server.py` identifies micro:bit devices by USB descriptors (`microbit`, `daplink`, `mbed` keywords) and hardware IDs. **Enhanced for v2 support** - detects VID:PID `0D28:0204` and v2-specific descriptors.

## Common Pitfalls

- **Unicode handling**: Protocol strips non-ASCII characters - see `format_message_command()`
- **Tool timeouts**: Always implement timeouts for micro:bit communication
- **Serial buffer**: micro:bit uses line-buffered input (`\n` terminated)
- **Music blocking**: Music playback blocks micro:bit execution until complete
- **Version differences**: v1 uses `uart` interface, v2 uses `sys.stdin` - firmware handles automatically
- **Port detection**: v2 boards may require different USB cables or appear with different descriptors