import asyncio
import signal
import sys

from .config import Config
from .remnawave import RemnawaveClient, NodeMonitor
from .cloudflare_dns import CloudflareClient, DNSManager
from .monitoring_service import MonitoringService
from .utils.logger import setup_logger


class GracefulExit(SystemExit):
    code = 0


def raise_graceful_exit(signum, frame):
    raise GracefulExit()


async def run_monitoring_loop(service: MonitoringService, interval: int, logger):
    logger.info(f"Starting monitoring loop with {interval}s interval")

    while True:
        try:
            await service.perform_health_check()

            logger.info(f"Waiting {interval} seconds until next check...")
            await asyncio.sleep(interval)

        except GracefulExit:
            logger.info("Received shutdown signal, stopping...")
            break
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, stopping...")
            break
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)
            logger.info(f"Retrying in {interval} seconds...")
            await asyncio.sleep(interval)


async def main():
    config = Config()

    logger = setup_logger(name="remnawave-cloudflare-monitor", level=config.log_level, log_file="logs/app.log")

    signal.signal(signal.SIGTERM, raise_graceful_exit)
    signal.signal(signal.SIGINT, raise_graceful_exit)

    logger.info("Starting Remnawave-Cloudflare DNS Monitor")
    logger.info(f"Check interval: {config.check_interval}s")

    remnawave_client = RemnawaveClient(api_url=config.remnawave_url, api_key=config.remnawave_api_key)

    node_monitor = NodeMonitor(remnawave_client)

    cloudflare_client = CloudflareClient(api_token=config.cloudflare_token)
    dns_manager = DNSManager(cloudflare_client)

    monitoring_service = MonitoringService(
        config=config, node_monitor=node_monitor, cloudflare_client=cloudflare_client, dns_manager=dns_manager
    )

    try:
        await monitoring_service.initialize_and_print_zones()

        await run_monitoring_loop(service=monitoring_service, interval=config.check_interval, logger=logger)
    except (GracefulExit, KeyboardInterrupt):
        logger.info("Shutting down gracefully")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Remnawave-Cloudflare DNS Monitor stopped")


if __name__ == "__main__":
    asyncio.run(main())
