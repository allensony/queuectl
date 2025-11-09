# QueueCTL - Background Job Queue System

**Flam Company Backend Developer Internship Assessment**

A production-grade CLI-based background job queue system implementing FIFO queuing, worker processes, exponential backoff retry mechanism, and Dead Letter Queue (DLQ) for failed jobs.

## 🎯 Features Implemented

### ✅ Must-Have Deliverables
- [x] **Working CLI Application** (`queuectl`)
- [x] **Persistent Job Storage** (JSON-based, survives restarts)
- [x] **Multiple Worker Support** (parallel job processing)
- [x] **Retry Mechanism with Exponential Backoff**
- [x] **Dead Letter Queue (DLQ)** for permanently failed jobs
- [x] **Configuration Management** via CLI

### 📋 Job Lifecycle States
1. **pending** → Waiting to be picked up by a worker
2. **processing** → Currently being executed
3. **completed** → Successfully executed
4. **failed** → Failed but retryable (moves back to pending)
5. **dead** → Permanently failed (moved to DLQ)

## 🚀 Quick Start

### Installation
No external dependencies required! Just Python 3.7+

```bash
# Clone or download the project
chmod +x queuectl.py
```

### Basic Usage

```bash
# 1. Enqueue some jobs
python queuectl.py enqueue '{"id":"job1","command":"echo Hello World"}'
python queuectl.py enqueue '{"id":"job2","command":"sleep 2"}'
python queuectl.py enqueue '{"id":"job3","command":"python -c \"print(2+2)\""}'

# 2. Start workers (in a separate terminal)
python queuectl.py worker start --count 3

# 3. Check queue status
python queuectl.py status

# 4. List jobs by state
python queuectl.py list --state completed
python queuectl.py list --state failed

# 5. Manage Dead Letter Queue
python queuectl.py dlq list
python queuectl.py dlq retry job1

# 6. Configure system
python queuectl.py config show
python queuectl.py config set --key max_retries --value 5
```

## 📚 Complete CLI Reference

### 1. `queuectl enqueue`
Add a new job to the queue.

```bash
python queuectl.py enqueue '{"id":"unique-id","command":"echo test"}'
```

**Job JSON Format:**
```json
{
  "id": "optional-unique-id",
  "command": "shell command to execute"
}
```

### 2. `queuectl worker`
Manage worker processes.

```bash
# Start 1 worker
python queuectl.py worker start

# Start 3 workers
python queuectl.py worker start --count 3

# Stop workers (Ctrl+C or)
python queuectl.py worker stop
```

### 3. `queuectl status`
Show queue statistics and active workers.

```bash
python queuectl.py status
```

Output:
```
=== Queue Status ===
Pending:    5
Processing: 2
Completed:  12
Failed:     1
Dead:       0
Active_workers: 3
```

### 4. `queuectl list`
List jobs by state.

```bash
python queuectl.py list --state pending
python queuectl.py list --state processing
python queuectl.py list --state completed
python queuectl.py list --state failed
python queuectl.py list --state dead
```

### 5. `queuectl dlq`
Manage Dead Letter Queue.

```bash
# List jobs in DLQ
python queuectl.py dlq list

# Retry a specific job from DLQ
python queuectl.py dlq retry job1
```

### 6. `queuectl config`
Configure system parameters.

```bash
# Show all configuration
python queuectl.py config show

# Set max retry attempts
python queuectl.py config set --key max_retries --value 5

# Set backoff base delay (seconds)
python queuectl.py config set --key backoff_base --value 2

# Set job timeout (seconds)
python queuectl.py config set --key job_timeout --value 600
```

## 🏗️ Architecture

### Job Lifecycle

```
pending → processing → completed
    ↓          ↓
    ↓       failed (retry with backoff)
    ↓          ↓
    └──────→ dead (moved to DLQ)
```

### Job Structure

```json
{
  "id": "unique-job-id",
  "command": "echo 'Hello World'",
  "state": "pending",
  "attempts": 0,
  "max_retries": 3,
  "created_at": "2025-11-04T10:30:00Z",
  "updated_at": "2025-11-04T10:30:00Z"
}
```

### Exponential Backoff Formula

```
delay = base * (2 ^ attempts) + jitter
```

Example with base=1:
- Attempt 1: ~1s
- Attempt 2: ~2s
- Attempt 3: ~4s
- Attempt 4: ~8s

## System Requirements

- Python 3.7+
- No external dependencies
- Works on Linux, macOS, Windows

## Testing

### Basic Flow Test

```bash
# Terminal 1: Start workers
python queuectl.py worker start --count 2

# Terminal 2: Enqueue jobs
python queuectl.py enqueue '{"id":"test1","command":"sleep 2"}'
python queuectl.py enqueue '{"id":"test2","command":"echo Success"}'
python queuectl.py enqueue '{"id":"test3","command":"false"}' # Will fail

# Check status
python queuectl.py status

# List completed jobs
python queuectl.py list --state completed
```

### Retry Test

```bash
# Enqueue a failing job
python queuectl.py enqueue '{"id":"fail1","command":"exit 1"}'

# Watch it retry (check logs)
# After max_retries, check DLQ
python queuectl.py dlq list

# Retry from DLQ
python queuectl.py dlq retry fail1
```

## Configuration Options

| Key | Default | Description |
|-----|---------|-------------|
| storage_file | jobs.json | Job storage file |
| max_retries | 3 | Maximum retry attempts |
| backoff_base | 1 | Base delay for exponential backoff (seconds) |
| backoff_max | 60 | Maximum backoff delay (seconds) |
| job_timeout | 300 | Job execution timeout (seconds) |

## Error Handling

- **Non-existent commands**: Job fails, retries with backoff
- **Timeout**: Job marked as failed after timeout
- **Max retries exceeded**: Job moved to DLQ
- **Worker interruption**: Current job released back to queue

## Design Decisions

1. **JSON Storage**: Lightweight, no database required
2. **File-based Locking**: Threading locks for concurrency
3. **Subprocess Execution**: Shell commands via subprocess
4. **Multiprocessing**: True parallelism for workers
5. **Signal Handling**: Graceful shutdown on SIGINT/SIGTERM

## Assumptions & Trade-offs

- JSON storage is not suitable for high-throughput systems
- File-based locking doesn't scale to distributed systems
- In-memory queue (could implement Redis backend)
- No job prioritization (FIFO only)
- No scheduled/delayed jobs

## Future Enhancements

- [ ] Job priority queues
- [ ] Scheduled jobs (run_at parameter)
- [ ] Job output logging
- [ ] Web dashboard
- [ ] Metrics and monitoring
- [ ] Redis backend option
- [ ] Job timeout handling

## License

MIT License - Free to use for placement assessment and beyond!
