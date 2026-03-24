# Logging Configuration

This project now includes comprehensive logging across all modules to help you track progress and debug issues. The logging system uses Python's standard `logging` module with configurable debug levels.

## Quick Start

### Running with Default Logging (INFO Level)

```bash
python app.py
```

This will show:
- Application startup and shutdown
- Mode transitions (command vs. LLM)
- Tool execution (without verbose details)
- Important operations (refunds, discounts, emails)

### Running with Debug Logging

```bash
LOG_LEVEL=DEBUG python app.py
```

This will show:
- All INFO messages
- Database connection details
- Command parsing and processing
- Policy decisions
- Detailed tool execution flow
- Audit log entries

### Running with Verbose Logging

```bash
LOG_LEVEL=DEBUG python app.py 2>&1 | tee app.log
```

This saves all output to both console and `app.log` file for later analysis.

## Logging Levels

The following logging levels are available (from least to most verbose):

| Level | What You See |
|-------|------|
| `CRITICAL` | Only critical failures |
| `ERROR` | Errors and critical failures |
| `WARNING` | Warnings, errors, and critical failures |
| `INFO` | Standard operational information (default) |
| `DEBUG` | Detailed debugging information |

## Examples

### Example 1: View All Database Operations

```bash
LOG_LEVEL=DEBUG python app.py
```

You'll see messages like:
```
2024-03-24 14:23:15 [DEBUG] db: Connecting to database: ecomm.sqlite
2024-03-24 14:23:15 [DEBUG] db: Database schema initialized
2024-03-24 14:23:15 [DEBUG] db: Seeding database with initial data
2024-03-24 14:23:15 [DEBUG] db: Seed products inserted (including malicious product)
```

### Example 2: Track Tool Execution

```bash
LOG_LEVEL=DEBUG python app.py
> search mug
```

You'll see:
```
2024-03-24 14:24:30 [DEBUG] app: Executing search command with query: mug
2024-03-24 14:24:30 [DEBUG] tools: search_products called with query: mug
2024-03-24 14:24:30 [DEBUG] db: Connecting to database: ecomm.sqlite
2024-03-24 14:24:30 [DEBUG] tools: search_products found 1 products
2024-03-24 14:24:30 [DEBUG] app: Result: status=success, has_data=True
```

### Example 3: Monitor Policy Decisions

```bash
LOG_LEVEL=DEBUG python app.py
> refund order_001 1000
```

You'll see:
```
2024-03-24 14:25:15 [DEBUG] app: Executing refund command for order: order_001, amount: 1000
2024-03-24 14:25:15 [DEBUG] tools: refund_order called: actor=cust_001, order=order_001, amount=1000
2024-03-24 14:25:15 [DEBUG] policy: authorize_tool_call: actor=cust_001, tool=refund_order, input={...}
2024-03-24 14:25:15 [DEBUG] policy: Tool call decision: allowed=True
2024-03-24 14:25:15 [DEBUG] db: Connecting to database: ecomm.sqlite
2024-03-24 14:25:15 [INFO] tools: Processing refund: order=order_001, amount=1000, total_refunded=1000
2024-03-24 14:25:15 [DEBUG] db: Audit log: actor=cust_001, action=refund_order, details={...}
```

### Example 4: View LLM Mode Startup

```bash
LOG_LEVEL=DEBUG python app.py
```

You'll see:
```
2024-03-24 14:26:00 [INFO] app: Application starting
2024-03-24 14:26:00 [DEBUG] app: Database path: ecomm.sqlite, Actor customer ID: cust_001
2024-03-24 14:26:00 [DEBUG] db: Connecting to database: ecomm.sqlite
2024-03-24 14:26:00 [INFO] db: Database initialization complete
2024-03-24 14:26:00 [INFO] app: Attempting to start LLM mode
2024-03-24 14:26:00 [INFO] app: Entering LLM mode
2024-03-24 14:26:00 [DEBUG] app: Using LLM model: eu.amazon.nova-2-lite-v1:0
2024-03-24 14:26:00 [DEBUG] app: Agent initialized with 6 tools
```

## Environment Variables

### `LOG_LEVEL`

Sets the logging level globally for the application.

```bash
# Valid values:
LOG_LEVEL=CRITICAL  # Only show critical errors
LOG_LEVEL=ERROR     # Show errors
LOG_LEVEL=WARNING   # Show warnings and errors
LOG_LEVEL=INFO      # Show info, warnings, and errors (default)
LOG_LEVEL=DEBUG     # Show all debug messages
```

**Default:** `INFO`

### Other Standard Variables

- `ACTOR_CUSTOMER_ID`: The customer ID logged in as (default: `cust_001`)
- `ECOMM_DB`: Path to SQLite database (default: `ecomm.sqlite`)
- `ENABLE_LLM`: Set to `0` to disable LLM mode and use command mode only
- `STRANDS_MODEL`: Override the LLM model ID

## Log Format

All log messages follow this format:

```
YYYY-MM-DD HH:MM:SS [LEVEL] module_name: message
```

Example:
```
2024-03-24 14:23:15 [DEBUG] tools: search_products called with query: mug
```

- **Date & Time**: When the event occurred
- **Level**: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Module Name**: Which Python module generated the log (app, db, tools, policy)
- **Message**: The actual log message

## Where Logging is Implemented

Logging has been added to these modules:

### `app.py`
- Application startup and shutdown
- Mode transitions (LLM vs. command)
- Command parsing and execution
- Tool invocation tracking

### `db.py`
- Database connections
- Schema initialization
- Data seeding
- Audit log entries

### `tools.py`
- Tool function calls
- Search/lookup operations
- Refund processing
- Discount application
- Email sending

### `policy.py`
- Policy decision logging
- Authorization checks
- Email recipient validation
- Refund policy evaluation

### `model_deployment/deploy.py`
- IAM role creation and retrieval
- Hugging Face model configuration
- SageMaker deployment progress
- Endpoint testing

## Tips and Tricks

### Save Logs to File
```bash
LOG_LEVEL=DEBUG python app.py > app.log 2>&1
```

### View Only Debug Messages
```bash
LOG_LEVEL=DEBUG python app.py 2>&1 | grep DEBUG
```

### View Only Tool Execution
```bash
LOG_LEVEL=DEBUG python app.py 2>&1 | grep tools
```

### Monitor Refunds and Sensitive Operations
```bash
LOG_LEVEL=DEBUG python app.py 2>&1 | grep -E "(refund|discount|email|audit)"
```

### Real-time Log Monitoring
```bash
LOG_LEVEL=DEBUG python app.py 2>&1 | tee >(tail -f app.log)
```

## Troubleshooting Missing Logs

If you don't see expected logs:

1. **Check the log level** - Use `LOG_LEVEL=DEBUG` to see all messages
2. **Check the module name** - Search for the right module name in output
3. **Check for exceptions** - Errors might be logged at WARNING or ERROR level

## Future Enhancements

When implementing guardrails, logging will help you:
- **Verify policy enforcement** - See which requests are being blocked
- **Audit sensitive operations** - Track who did what and when
- **Debug integration issues** - Understand the flow of data through tools
- **Monitor compliance** - Ensure guardrails are working as expected
