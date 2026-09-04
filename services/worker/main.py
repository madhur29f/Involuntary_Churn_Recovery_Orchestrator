import asyncio, os
from temporalio.client import Client
from temporalio.worker import Worker
from .workflows import RecoveryWorkflow
from .activities import classify_recovery, evaluate_simulated_payment

from services.api.store import get_system_state

async def main():
    retries = 30
    client = None
    while retries > 0:
        try:
            client = await Client.connect(os.getenv("TEMPORAL_ADDRESS", "temporal:7233"))
            break
        except Exception as e:
            retries -= 1
            print(f"Waiting for Temporal frontend ({e})... retrying in 2s")
            await asyncio.sleep(2)
    if not client:
        raise RuntimeError("Could not connect to Temporal")
    print("Temporal Worker connected successfully. Starting listening loop...")

    while True:
        if get_system_state("worker_chaos_paused", "0") == "1":
            await asyncio.sleep(1)
            continue

        worker = Worker(
            client,
            task_queue=os.getenv("TEMPORAL_TASK_QUEUE", "recovery-orchestrator"),
            workflows=[RecoveryWorkflow],
            activities=[classify_recovery, evaluate_simulated_payment]
        )
        worker_task = asyncio.create_task(worker.run())
        print("Worker polling task queue active.")

        while not worker_task.done():
            if get_system_state("worker_chaos_paused", "0") == "1":
                print("[CHAOS CONTROL] Kill signal detected! Halting worker poller...")
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass
                break
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
