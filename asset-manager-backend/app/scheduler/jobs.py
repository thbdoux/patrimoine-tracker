from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.sync_service import SyncService


def setup_scheduler(sync_service: SyncService) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    # Powens — toutes les 6h (respecte les limites DSP2)
    scheduler.add_job(
        sync_service.run_sync,
        trigger="interval",
        args=["powens"],
        hours=6,
        id="sync_powens",
        max_instances=1,
        coalesce=True,
    )

    # Binance — toutes les 5 minutes
    scheduler.add_job(
        sync_service.run_sync,
        trigger="interval",
        args=["binance"],
        minutes=5,
        id="sync_binance",
        max_instances=1,
        coalesce=True,
    )

    return scheduler
