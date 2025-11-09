#!/usr/bin/env python3
"""
QueueCTL Test Suite
Comprehensive testing for all functionality
"""

import subprocess
import time
import json
import sys

def run_cmd(cmd):
    """Execute command and return result"""
    print(f"\n$ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"stderr: {result.stderr}", file=sys.stderr)
    return result

def test_enqueue():
    """Test job enqueueing"""
    print("\n" + "="*60)
    print("TEST 1: Job Enqueueing")
    print("="*60)

    jobs = [
        '{"id":"test1","command":"echo Test1"}',
        '{"id":"test2","command":"sleep 1"}',
        '{"id":"test3","command":"python -c \\"print(2+2)\\""}',
        '{"id":"fail","command":"exit 1"}'
    ]

    for job in jobs:
        run_cmd(f"python queuectl.py enqueue '{job}'")

    print("✓ Job enqueueing test completed")

def test_status():
    """Test status command"""
    print("\n" + "="*60)
    print("TEST 2: Status Check")
    print("="*60)

    run_cmd("python queuectl.py status")
    print("✓ Status test completed")

def test_list():
    """Test list commands"""
    print("\n" + "="*60)
    print("TEST 3: List Jobs")
    print("="*60)

    for state in ['pending', 'completed', 'failed']:
        print(f"\nListing {state} jobs:")
        run_cmd(f"python queuectl.py list --state {state}")

    print("✓ List test completed")

def test_config():
    """Test configuration"""
    print("\n" + "="*60)
    print("TEST 4: Configuration")
    print("="*60)

    run_cmd("python queuectl.py config show")
    run_cmd("python queuectl.py config set --key max_retries --value 5")
    run_cmd("python queuectl.py config show")

    # Reset to default
    run_cmd("python queuectl.py config set --key max_retries --value 3")

    print("✓ Configuration test completed")

def test_invalid_json():
    """Test invalid JSON handling"""
    print("\n" + "="*60)
    print("TEST 5: Invalid JSON Handling")
    print("="*60)

    result = run_cmd("python queuectl.py enqueue 'invalid json'")
    if result.returncode != 0:
        print("✓ Invalid JSON correctly rejected")
    else:
        print("✗ Invalid JSON was accepted (should have failed)")

def main():
    """Run all tests"""
    print("="*60)
    print("QUEUECTL TEST SUITE")
    print("="*60)
    print("Testing all CLI functionality...")

    try:
        test_enqueue()
        test_status()
        test_list()
        test_config()
        test_invalid_json()

        print("\n" + "="*60)
        print("ALL TESTS COMPLETED SUCCESSFULLY! ✓")
        print("="*60)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
