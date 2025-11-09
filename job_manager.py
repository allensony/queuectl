"""
Job Manager - Persistent storage and queue management
Handles job lifecycle, state transitions, and DLQ operations
"""

import json
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional
import uuid

class JobManager:
    """Manages job storage, queueing, and state transitions"""

    def __init__(self, config):
        self.config = config
        self.storage_file = config.get('storage_file', 'jobs.json')
        self.lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self):
        """Initialize storage file if it doesn't exist"""
        if not os.path.exists(self.storage_file):
            initial_data = {'jobs': {}, 'workers': {}}
            self._save_data(initial_data)

    def _load_data(self) -> Dict:
        """Thread-safe data loading"""
        try:
            with open(self.storage_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'jobs': {}, 'workers': {}}

    def _save_data(self, data: Dict):
        """Atomic write to storage file"""
        temp_file = self.storage_file + '.tmp'
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file, self.storage_file)

    def enqueue(self, job_data: Dict) -> str:
        """Add new job to queue with FIFO ordering"""
        with self.lock:
            data = self._load_data()

            job_id = job_data.get('id', str(uuid.uuid4()))

            job = {
                'id': job_id,
                'command': job_data.get('command', ''),
                'state': 'pending',
                'attempts': 0,
                'max_retries': self.config.get('max_retries', 3),
                'created_at': datetime.utcnow().isoformat() + 'Z',
                'updated_at': datetime.utcnow().isoformat() + 'Z'
            }

            data['jobs'][job_id] = job
            self._save_data(data)
            return job_id

    def get_next_job(self) -> Optional[Dict]:
        """Get next pending job (FIFO) and mark as processing"""
        with self.lock:
            data = self._load_data()

            # Find oldest pending job
            pending_jobs = [
                (jid, job) for jid, job in data['jobs'].items()
                if job['state'] == 'pending'
            ]

            if not pending_jobs:
                return None

            # Sort by created_at for FIFO
            pending_jobs.sort(key=lambda x: x[1]['created_at'])
            job_id, job = pending_jobs[0]

            # Mark as processing
            job['state'] = 'processing'
            job['updated_at'] = datetime.utcnow().isoformat() + 'Z'
            self._save_data(data)

            return job

    def update_job_state(self, job_id: str, state: str, error: str = None) -> bool:
        """Update job state with retry logic and DLQ handling"""
        with self.lock:
            data = self._load_data()

            if job_id not in data['jobs']:
                return False

            job = data['jobs'][job_id]
            job['state'] = state
            job['updated_at'] = datetime.utcnow().isoformat() + 'Z'

            if error:
                job['error'] = error

            # Handle failed jobs with retry logic
            if state == 'failed':
                job['attempts'] += 1

                if job['attempts'] >= job['max_retries']:
                    # Move to Dead Letter Queue
                    job['state'] = 'dead'
                    print(f"Job {job_id} moved to DLQ after {job['attempts']} attempts")
                else:
                    # Retry: reset to pending
                    job['state'] = 'pending'
                    print(f"Job {job_id} will retry (attempt {job['attempts']}/{job['max_retries']})")

            self._save_data(data)
            return True

    def get_status(self) -> Dict:
        """Get comprehensive queue statistics"""
        with self.lock:
            data = self._load_data()

            stats = {
                'pending': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0,
                'dead': 0,
                'active_workers': len(data.get('workers', {}))
            }

            for job in data['jobs'].values():
                state = job['state']
                if state in stats:
                    stats[state] += 1

            return stats

    def list_jobs(self, state: str) -> List[Dict]:
        """List all jobs in specified state"""
        with self.lock:
            data = self._load_data()
            jobs = [job for job in data['jobs'].values() if job['state'] == state]
            # Sort by created_at
            jobs.sort(key=lambda x: x['created_at'])
            return jobs

    def list_dlq(self) -> List[Dict]:
        """List jobs in Dead Letter Queue"""
        return self.list_jobs('dead')

    def retry_from_dlq(self, job_id: str) -> bool:
        """Move job from DLQ back to pending queue"""
        with self.lock:
            data = self._load_data()

            if job_id not in data['jobs']:
                return False

            job = data['jobs'][job_id]

            if job['state'] != 'dead':
                return False

            # Reset job for retry
            job['state'] = 'pending'
            job['attempts'] = 0
            job['updated_at'] = datetime.utcnow().isoformat() + 'Z'
            if 'error' in job:
                del job['error']

            self._save_data(data)
            return True

    def register_worker(self, worker_id: str):
        """Register active worker process"""
        with self.lock:
            data = self._load_data()
            data['workers'][worker_id] = {
                'started_at': datetime.utcnow().isoformat() + 'Z',
                'pid': os.getpid()
            }
            self._save_data(data)

    def unregister_worker(self, worker_id: str):
        """Unregister worker on shutdown"""
        with self.lock:
            data = self._load_data()
            if worker_id in data['workers']:
                del data['workers'][worker_id]
                self._save_data(data)

    def cleanup_stale_jobs(self):
        """Reset processing jobs to pending (for crash recovery)"""
        with self.lock:
            data = self._load_data()

            for job in data['jobs'].values():
                if job['state'] == 'processing':
                    job['state'] = 'pending'

            self._save_data(data)
