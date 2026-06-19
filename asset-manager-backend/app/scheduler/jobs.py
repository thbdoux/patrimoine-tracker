from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.sync_service import SyncService


def setup_scheduler(sync_service: SyncService) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    # Powens — toutes les 12h (2x/jour)
    scheduler.add_job(
        sync_service.run_sync,
        trigger="interval",
        args=["powens"],
        hours=1,
        id="sync_powens",
        max_instances=1,
        coalesce=True,
    )

    # Binance — toutes les 12h (2x/jour)
    scheduler.add_job(
        sync_service.run_sync,
        trigger="interval",
        args=["binance"],
        hours=1,
        id="sync_binance",
        max_instances=1,
        coalesce=True,
    )

    # Enable Banking (PSD2) — toutes les heures
    scheduler.add_job(
        sync_service.run_sync,
        trigger="interval",
        args=["enablebanking"],
        hours=1,
        id="sync_enablebanking",
        max_instances=1,
        coalesce=True,
    )

    return scheduler
