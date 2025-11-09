#!/usr/bin/env python3
"""
QueueCTL - Background Job Queue System
Main CLI entry point for Flam Company Placement Assessment
Author: Student Submission
"""

import argparse
import sys
import json
from job_manager import JobManager
from worker import Worker
from config import Config

def main():
    parser = argparse.ArgumentParser(
        prog='queuectl',
        description='CLI-based background job queue system with retry and DLQ',
        epilog='Use queuectl <command> --help for more information'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Enqueue command
    enqueue_parser = subparsers.add_parser('enqueue', help='Add a new job to the queue')
    enqueue_parser.add_argument('job_data', help='Job data in JSON format')

    # Worker command
    worker_parser = subparsers.add_parser('worker', help='Start/stop worker processes')
    worker_parser.add_argument('action', choices=['start', 'stop'], help='Action to perform')
    worker_parser.add_argument('--count', type=int, default=1, help='Number of workers')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show queue status')

    # List command
    list_parser = subparsers.add_parser('list', help='List jobs by state')
    list_parser.add_argument('--state', choices=['pending', 'processing', 'completed', 'failed', 'dead'],
                            default='pending', help='Job state filter')

    # DLQ commands
    dlq_parser = subparsers.add_parser('dlq', help='Dead Letter Queue operations')
    dlq_subparsers = dlq_parser.add_subparsers(dest='dlq_action')
    dlq_list = dlq_subparsers.add_parser('list', help='List DLQ jobs')
    dlq_retry = dlq_subparsers.add_parser('retry', help='Retry job from DLQ')
    dlq_retry.add_argument('job_id', help='Job ID to retry')

    # Config commands
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_parser.add_argument('action', choices=['show', 'set'])
    config_parser.add_argument('--key', help='Config key')
    config_parser.add_argument('--value', help='Config value')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = Config()
    job_manager = JobManager(config)

    if args.command == 'enqueue':
        try:
            job_data = json.loads(args.job_data)
            job_id = job_manager.enqueue(job_data)
            print(f"✓ Job {job_id} enqueued successfully")
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'worker':
        worker = Worker(job_manager, config, worker_count=args.count)
        if args.action == 'start':
            print(f"Starting {args.count} worker(s)...")
            worker.start()
        else:
            worker.stop()

    elif args.command == 'status':
        status = job_manager.get_status()
        print("\n=== Queue Status ===")
        for state, count in status.items():
            print(f"{state.capitalize()}: {count}")

    elif args.command == 'list':
        jobs = job_manager.list_jobs(args.state)
        print(f"\n=== {args.state.upper()} Jobs ===")
        for job in jobs:
            print(f"[{job['id']}] {job['command']} (attempts: {job['attempts']})")

    elif args.command == 'dlq':
        if args.dlq_action == 'list':
            jobs = job_manager.list_dlq()
            print("\n=== Dead Letter Queue ===")
            for job in jobs:
                print(f"[{job['id']}] {job['command']}")
        elif args.dlq_action == 'retry':
            if job_manager.retry_from_dlq(args.job_id):
                print(f"✓ Job {args.job_id} requeued")
            else:
                print(f"✗ Job {args.job_id} not found", file=sys.stderr)

    elif args.command == 'config':
        if args.action == 'show':
            config.show()
        else:
            config.set(args.key, args.value)
            print(f"✓ Config updated: {args.key} = {args.value}")

if __name__ == '__main__':
    main()
