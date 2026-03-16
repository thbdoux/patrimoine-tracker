import argparse
import asyncio
import sys

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.connectors.registry import ConnectorRegistry
from app.scheduler.jobs import setup_scheduler
from app.services.snapshot_service import SnapshotService
from app.services.sync_service import SyncService


def configure_logging() -> None:
    import logging
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def build_services() -> tuple[ConnectorRegistry, SyncService]:
    registry = ConnectorRegistry()
    registry.discover()
    snapshot_service = SnapshotService()
    sync_service = SyncService(registry, snapshot_service)
    return registry, sync_service


def create_app() -> FastAPI:
    app = FastAPI(
        title="Patrimoine Tracker API",
        description="API de suivi du patrimoine financier",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


async def sync_now(source_name: str) -> None:
    _, sync_service = build_services()
    await sync_service.run_sync(source_name)


async def run_scheduler() -> None:
    registry, sync_service = build_services()
    scheduler = setup_scheduler(sync_service)
    scheduler.start()

    logger = structlog.get_logger(__name__)
    logger.info("scheduler_started", sources=registry.source_names())

    if settings.sync_on_startup:
        logger.info("sync_on_startup", sources=registry.source_names())
        tasks = [sync_service.run_sync(name) for name in registry.source_names()]
        await asyncio.gather(*tasks, return_exceptions=True)

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("scheduler_stopping")
        scheduler.shutdown()


async def run_all() -> None:
    """Run FastAPI server and scheduler concurrently in the same event loop."""
    app = create_app()
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)

    await asyncio.gather(
        server.serve(),
        run_scheduler(),
    )


def main() -> None:
    configure_logging()

    parser = argparse.ArgumentParser(description="Patrimoine Tracker")
    parser.add_argument(
        "--sync-now",
        metavar="SOURCE",
        help="Déclenche une sync immédiate pour la source spécifiée et quitte (ex: binance, powens)",
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Lance uniquement le serveur API sans le scheduler",
    )
    args = parser.parse_args()

    if args.sync_now:
        asyncio.run(sync_now(args.sync_now))
    elif args.api_only:
        app = create_app()
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        asyncio.run(run_all())


if __name__ == "__main__":
    main()
