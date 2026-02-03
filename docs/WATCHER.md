# Directory Watcher Quick Reference

## Overview

The `pngx-cao upload watch` command provides a daemon-like service that monitors a directory for new document folders and automatically uploads them to Paperless-ngx.

## Basic Usage

```bash
pngx-cao upload watch /path/to/originals
```

## How It Works

```txt
┌─────────────────────────────────────────────────────────────┐
│                    Directory Watcher Flow                    │
└─────────────────────────────────────────────────────────────┘

1. POLL (every poll-interval seconds)
   └─> Scan watch directory for new folders
   
2. DETECT NEW FOLDER
   └─> Check if folder is already processed
       ├─> Yes: Skip
       └─> No: Continue to stabilization
       
3. STABILIZE (wait stability-wait seconds)
   └─> Monitor folder for file changes
       ├─> Still changing: Skip this cycle, retry next poll
       └─> Stable: Continue to upload
       
4. UPLOAD
   └─> Call upload service (same as 'upload folder')
       ├─> Success: Mark as processed
       └─> Failure: Log error, mark as processed (won't retry)
       
5. REPEAT
   └─> Return to step 1
```

## Configuration Parameters

### Poll Interval

- **Default**: 5.0 seconds
- **Purpose**: How often to scan the directory
- **Tuning**:
  - Lower (1-2s): More responsive, higher CPU usage
  - Higher (10-30s): Less responsive, lower CPU usage
  - Network shares: Use higher values (30-60s)

```bash
# Check every 2 seconds (fast)
pngx-cao upload watch ./originals --poll-interval 2

# Check every 30 seconds (conservative)
pngx-cao upload watch ./originals --poll-interval 30
```

### Stability Wait

- **Default**: 2.0 seconds
- **Purpose**: How long to wait for no file changes
- **Tuning**:
  - Archives being extracted: 5-10s
  - Network copies: 5-10s
  - Local operations: 1-2s

```bash
# Wait 5 seconds for stability (slow extractions)
pngx-cao upload watch ./originals --stability-wait 5

# Wait 1 second (fast local operations)
pngx-cao upload watch ./originals --stability-wait 1
```

## Duplicate Handling

Same as batch/folder upload:

```bash
# Skip duplicates (default)
pngx-cao upload watch ./originals --duplicate-handling skip

# Replace existing documents
pngx-cao upload watch ./originals --duplicate-handling replace

# Update metadata only
pngx-cao upload watch ./originals --duplicate-handling update-metadata
```

## Running as a Service

### Background Process (Linux/macOS)

```bash
# Start in background
nohup pngx-cao upload watch ./originals > watcher.log 2>&1 &

# Get process ID
echo $!

# Stop (replace PID with actual process ID)
kill <PID>

# View logs
tail -f watcher.log
```

### Systemd Service (Linux)

See `docs/pngx-cao-watcher.service.example` for a complete systemd service file.

```bash
# Install service
sudo cp docs/pngx-cao-watcher.service.example /etc/systemd/system/pngx-cao-watcher.service
sudo systemctl daemon-reload

# Start service
sudo systemctl start pngx-cao-watcher

# Enable on boot
sudo systemctl enable pngx-cao-watcher

# Check status
sudo systemctl status pngx-cao-watcher

# View logs
sudo journalctl -u pngx-cao-watcher -f
```

### Docker Container

Example Dockerfile snippet:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

# Create watch directory
RUN mkdir -p /data/originals

CMD ["pngx-cao", "upload", "watch", "/data/originals"]
```

## Integration Examples

### With Archive Extraction

```bash
#!/bin/bash
# extract-and-watch.sh

ARCHIVE_DIR="/downloads/archives"
EXTRACT_DIR="/data/originals"
WATCH_DIR="/data/originals"

# Start watcher in background
pngx-cao upload watch "$WATCH_DIR" --stability-wait 5 &
WATCHER_PID=$!

# Watch for archives and extract them
inotifywait -m -e create "$ARCHIVE_DIR" --format '%f' | while read file; do
    if [[ $file == *.zip ]]; then
        echo "Extracting $file..."
        unzip -q "$ARCHIVE_DIR/$file" -d "$EXTRACT_DIR/"
    fi
done

# Cleanup on exit
trap "kill $WATCHER_PID" EXIT
```

### With Cron for Scheduled Downloads

```bash
# crontab -e
# Download reports every hour, watcher uploads them automatically

0 * * * * /usr/local/bin/download-reports.sh /data/originals
```

### With Webhook/API Trigger

```python
from flask import Flask, request
import subprocess
import shutil

app = Flask(__name__)

@app.route('/webhook/new-report', methods=['POST'])
def handle_new_report():
    """Copy report to watched directory when webhook received."""
    report_path = request.json['report_path']
    dest = f"/data/originals/{Path(report_path).name}"
    shutil.copytree(report_path, dest)
    return {'status': 'accepted'}

# Watcher runs separately and picks up the new folder
```

## Monitoring

### Check Watcher is Running

```bash
# Find process
ps aux | grep "pngx-cao upload watch"

# Check systemd status
sudo systemctl status pngx-cao-watcher
```

### View Processed Count

Enable debug logging to see processing statistics:

```bash
pngx-cao upload watch ./originals --debug
```

Output shows:

- Folders detected
- Stability checks
- Upload results
- Processed count

### Log Analysis

```bash
# Find errors
grep -i error watcher.log

# Count processed documents
grep "Successfully uploaded" watcher.log | wc -l

# Recent activity
tail -n 50 watcher.log
```

## Troubleshooting

### Folder Not Being Processed

1. **Check folder exists**: `ls -la /path/to/originals/folder-name`
2. **Check stability**: Files might still be changing
3. **Check logs**: Look for "unstable" messages
4. **Increase stability-wait**: `--stability-wait 10`

### High CPU Usage

1. **Increase poll-interval**: `--poll-interval 30`
2. **Check for file system issues**: Network latency, slow I/O
3. **Reduce debug logging**: Remove `--debug` flag

### Watcher Stopped Unexpectedly

1. **Check system logs**: `journalctl -xe` or `dmesg`
2. **Check disk space**: `df -h`
3. **Check permissions**: Ensure read access to watch directory
4. **Check API connectivity**: Paperless-ngx might be down

### Already Processed Folders

The watcher tracks processed folders in memory. To reprocess:

1. **Restart watcher**: Clears in-memory tracking
2. **Move folder out and back**: `mv folder folder.tmp && mv folder.tmp folder`
3. **Use batch command instead**: `pngx-cao upload batch`

## Performance Guidelines

| Scenario | Poll Interval | Stability Wait |
|----------|---------------|----------------|
| Local SSD, manual drops | 2-5s | 1-2s |
| Local HDD, archive extraction | 5-10s | 5-10s |
| Network share (NFS/SMB) | 30-60s | 10-30s |
| High-volume automation | 10-30s | 2-5s |
| Low-power device (Raspberry Pi) | 30-60s | 5-10s |

## Best Practices

✅ **Do**:

- Test with `--dry-run` first
- Monitor logs when starting
- Use systemd for production
- Set appropriate poll/stability intervals
- Use `--debug` for troubleshooting

❌ **Don't**:

- Use very low poll intervals (<1s) unless needed
- Run multiple watchers on same directory
- Manually modify folders while being processed
- Ignore error logs
- Run without proper file permissions

## Security Considerations

- Watcher needs read access to watch directory
- API credentials are stored in environment/config
- Consider using systemd's security features:
  - `NoNewPrivileges=true`
  - `ProtectSystem=strict`
  - `ReadWritePaths=` for specific directories
- Run as dedicated user with minimal permissions
- Use SSL/TLS for Paperless-ngx connection
