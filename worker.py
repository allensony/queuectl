"""
Worker - Job execution with retry and exponential backoff
Implements multiprocessing worker pool with graceful shutdown
"""

import subprocess
import time
import signal
import sys
import os
import multiprocessing as mp
from typing import Dict
import random

class Worker:
    """Worker process that executes jobs from the queue"""

    def __init__(self, job_manager, config, worker_count=1):
        self.job_manager = job_manager
        self.config = config
        self.worker_count = worker_count
        self.running = True
        self.processes = []

        # Setup graceful shutdown handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        signal_names = {signal.SIGINT: 'SIGINT', signal.SIGTERM: 'SIGTERM'}
        print(f"\n[SHUTDOWN] Received {signal_names.get(signum, signum)}")
        print("[SHUTDOWN] Waiting for current jobs to complete...")
        self.running = False

    def _calculate_backoff(self, attempts: int) -> float:
        """Calculate exponential backoff delay with jitter"""
        base = self.config.get('backoff_base', 1)
        max_delay = self.config.get('backoff_max', 60)

        # Exponential backoff: base * 2^attempts
        delay = base * (2 ** attempts)

        # Add jitter to prevent thundering herd
        jitter = random.uniform(0, 1)
        delay += jitter

        return min(delay, max_delay)

    def _execute_job(self, job: Dict) -> bool:
        """Execute a single job using subprocess"""
        job_id = job['id']
        command = job['command']
        timeout = self.config.get('job_timeout', 300)

        print(f"[{job_id}] Executing: {command}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                print(f"[{job_id}] ✓ SUCCESS (exit code 0)")
                if result.stdout:
                    print(f"[{job_id}] Output: {result.stdout.strip()}")
                self.job_manager.update_job_state(job_id, 'completed')
                return True
            else:
                error = f"Exit code {result.returncode}"
                if result.stderr:
                    error += f": {result.stderr.strip()}"

                print(f"[{job_id}] ✗ FAILED - {error}")
                self.job_manager.update_job_state(job_id, 'failed', error)
                return False

        except subprocess.TimeoutExpired:
            error = f"Timeout after {timeout}s"
            print(f"[{job_id}] ✗ TIMEOUT - {error}")
            self.job_manager.update_job_state(job_id, 'failed', error)
            return False

        except Exception as e:
            error = str(e)
            print(f"[{job_id}] ✗ ERROR - {error}")
            self.job_manager.update_job_state(job_id, 'failed', error)
            return False

    def _worker_loop(self, worker_id: str):
        """Main worker event loop"""
        self.job_manager.register_worker(worker_id)
        print(f"[{worker_id}] Started (PID: {os.getpid()})")

        try:
            while self.running:
                job = self.job_manager.get_next_job()

                if job is None:
                    # No jobs available - wait briefly
                    time.sleep(1)
                    continue

                # Apply exponential backoff for retries
                if job['attempts'] > 0:
                    backoff = self._calculate_backoff(job['attempts'])
                    print(f"[{job['id']}] Retry #{job['attempts']} - waiting {backoff:.2f}s")

                    # Check for shutdown during backoff
                    for _ in range(int(backoff * 10)):
                        if not self.running:
                            break
                        time.sleep(0.1)

                    if not self.running:
                        # Release job back to queue on shutdown
                        self.job_manager.update_job_state(job['id'], 'pending')
                        break

                # Execute the job
                self._execute_job(job)

        except KeyboardInterrupt:
            print(f"[{worker_id}] Interrupted")

        finally:
            self.job_manager.unregister_worker(worker_id)
            print(f"[{worker_id}] Stopped")

    def start(self):
        """Start worker processes"""
        # Clean up any stale jobs from previous crash
        self.job_manager.cleanup_stale_jobs()

        for i in range(self.worker_count):
            worker_id = f"worker-{os.getpid()}-{i+1}"
            process = mp.Process(
                target=self._worker_loop,
                args=(worker_id,),
                name=worker_id
            )
            process.start()
            self.processes.append(process)

        # Wait for all processes to complete
        try:
            for process in self.processes:
                process.join()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop all workers gracefully"""
        self.running = False

        print("[SHUTDOWN] Stopping workers...")

        for process in self.processes:
            if process.is_alive():
                # Give process time to finish current job
                process.join(timeout=10)

                if process.is_alive():
                    print(f"[SHUTDOWN] Force terminating {process.name}")
                    process.terminate()
                    process.join(timeout=5)

                    if process.is_alive():
                        process.kill()
                        process.join()

        print("[SHUTDOWN] All workers stopped")
