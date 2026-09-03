import asyncio, os
from temporalio.client import Client
from temporalio.worker import Worker
from .workflows import RecoveryWorkflow
from .activities import classify_recovery, evaluate_simulated_payment

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
    worker = Worker(client, task_queue=os.getenv("TEMPORAL_TASK_QUEUE", "recovery-orchestrator"),
                    workflows=[RecoveryWorkflow], activities=[classify_recovery, evaluate_simulated_payment])
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
