import asyncio
import sys
import logging
from app.workers.background_workers import outbound_queue_delivery_worker, waha_monitor_worker
from app.services.logging_service import configure_logging

if __name__ == "__main__":
    configure_logging()
    if len(sys.argv) < 2:
        print("Usage: python worker_cli.py <outbound|monitor>")
        sys.exit(1)
        
    worker_type = sys.argv[1]
    
    if worker_type == "outbound":
        logging.info("Starting outbound-worker...")
        asyncio.run(outbound_queue_delivery_worker())
    elif worker_type == "monitor":
        logging.info("Starting waha-monitor...")
        asyncio.run(waha_monitor_worker())
    elif worker_type == "bootstrap":
        logging.info("Starting bootstrap...")
        
        async def run_bootstrap() -> None:
            from app.db import SessionLocal, engine
            from app.services.faq_service import FAQService
            from pathlib import Path
            from sqlalchemy import text
            
            CORE_FAQ_PATH = Path("core_faq.md")
            if not CORE_FAQ_PATH.exists():
                CORE_FAQ_PATH = Path(__file__).resolve().parent / "core_faq.md"
                
            async with SessionLocal() as session:
                lock_acquired = False
                try:
                    # Blocking advisory lock with 60s timeout
                    await session.execute(text("SET statement_timeout = '60s'"))
                    await session.execute(text("SELECT pg_advisory_lock(42000001)"))
                    lock_acquired = True
                    await session.execute(text("SET statement_timeout = '0'"))
                    
                    logging.info("FAQ bootstrap lock acquired, running sync...")
                    service = FAQService(session)
                    report = await service.load_faq_report_from_file(str(CORE_FAQ_PATH))
                    await session.commit()
                    logging.info(f"faq_bootstrap_completed: {report}")
                except Exception as exc:
                    logging.error(f"faq_bootstrap_failed: {exc}", exc_info=True)
                    sys.exit(1)
                finally:
                    if lock_acquired:
                        try:
                            await session.execute(text("SELECT pg_advisory_unlock(42000001)"))
                            await session.commit()
                        except Exception:
                            pass
            await engine.dispose()
            
        asyncio.run(run_bootstrap())
    else:
        print(f"Unknown worker type: {worker_type}")
        sys.exit(1)

