<p align="center">
  <img src="https://raw.githubusercontent.com/hteppl/remnawave-cloudflare-nodes/master/.github/images/logo.png" alt="remnawave-cloudflare-nodes" width="800px">
</p>

## remnawave-cloudflare-nodes

<p align="left">
  <a href="https://github.com/hteppl/remnawave-cloudflare-nodes/releases/"><img src="https://img.shields.io/github/v/release/hteppl/remnawave-cloudflare-nodes.svg" alt="Release"></a>
  <a href="https://hub.docker.com/r/hteppl/remnawave-cloudflare-nodes/"><img src="https://img.shields.io/badge/DockerHub-remnawave--cloudflare--nodes-blue" alt="DockerHub"></a>
  <a href="https://github.com/hteppl/remnawave-cloudflare-nodes/actions"><img src="https://img.shields.io/github/actions/workflow/status/hteppl/remnawave-cloudflare-nodes/dockerhub-publish.yaml" alt="Build"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.12-blue.svg" alt="Python 3.12"></a>
  <a href="https://opensource.org/licenses/GPL-3.0"><img src="https://img.shields.io/badge/license-GPLv3-green.svg" alt="License: GPL v3"></a>
</p>

Automatically manage Cloudflare DNS records based on Remnawave (https://docs.rw) node health status.

## Features

- **Automatic Health Monitoring** - Continuously monitors node health status via Remnawave API
- **Dynamic DNS Management** - Adds DNS records for healthy nodes, removes records for unhealthy ones
- **Auto Zone Discovery** - Automatically discovers Cloudflare zone IDs from domain names
- **Multi-Domain Support** - Manage multiple domains with multiple DNS zones each
- **Configurable Intervals** - Set custom health check intervals
- **Docker Ready** - Easy deployment with Docker and Docker Compose

## Prerequisites

Before you begin, ensure you have the following:

- **Remnawave Panel** with nodes configured
- **Remnawave API Token** - Generate from your Remnawave panel settings
- **Cloudflare Account** with DNS zones configured
- **Cloudflare API Token** - Create with DNS edit permissions

## Configuration

Copy [`.env.example`](.env.example) to `.env` and fill in your values:

```env
# Remnawave API Configuration
REMNAWAVE_API_URL=https://panel.example.com
REMNAWAVE_API_KEY=remnawave_api_key

# Cloudflare API Configuration
CLOUDFLARE_API_TOKEN=cloudflare_api_token
```

Copy [`config.example.yml`](config.example.yml) to `config.yml` and configure your domains:

```yaml
remnawave:
  check-interval: 30

domains:
  - domain: example.com
    zones:
      - name: s1
        ttl: 120
        proxied: false
        ips:
          - 1.2.3.4
          - 5.6.7.8

logging:
  level: INFO
```

### Configuration Reference

| Variable                | Description                                        | Default | Required |
|-------------------------|----------------------------------------------------|---------|----------|
| `REMNAWAVE_API_URL`     | Remnawave API endpoint to fetch nodes from         | -       | Yes      |
| `REMNAWAVE_API_KEY`     | API authentication token                           | -       | Yes      |
| `CLOUDFLARE_API_TOKEN`  | Cloudflare API token with DNS edit permissions     | -       | Yes      |
| `check-interval`        | Interval in seconds between health checks          | 30      | No       |
| `logging.level`         | Log level (DEBUG, INFO, WARNING, ERROR)            | INFO    | No       |

## Installation

### Docker (recommended)

1. Create the docker-compose.yml:

```yaml
services:
  remnawave-cloudflare-nodes:
    image: hteppl/remnawave-cloudflare-nodes:latest
    container_name: remnawave-cloudflare-nodes
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./config.yml:/app/config.yml:ro
      - ./logs:/app/logs
    logging:
      driver: json-file
      options:
        max-size: "20m"
        max-file: "3"
```

2. Create and configure your environment file:

```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

3. Start the container:

```bash
docker compose up -d && docker compose logs -f
```

### Manual Installation

1. Clone the repository:

```bash
git clone https://github.com/hteppl/remnawave-cloudflare-nodes.git
cd remnawave-cloudflare-nodes
```

2. Create a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create and configure your environment file:

```bash
cp .env.example .env
```

5. Run the application:

```bash
python -m src
```

## How It Works

1. **Initial Fetch** - On startup, the service fetches all nodes from the Remnawave API and auto-discovers
   Cloudflare zone IDs

2. **Health Evaluation** - Based on node status, determines which nodes are healthy:
   - Node must be connected (`is_connected = true`)
   - Node must not be disabled (`is_disabled = false`)
   - Node must have Xray installed (`xray_version` is not null)

3. **DNS Synchronization** - For each configured zone:
   - Adds DNS A records for IPs that are both configured AND healthy
   - Removes DNS A records for IPs that are no longer healthy

4. **Continuous Updates** - The service polls the Remnawave API at the configured interval (`check-interval`) and
   updates DNS records

The service manages DNS records dynamically, ensuring only healthy nodes are included in DNS resolution.

### Logs

Monitor logs to diagnose issues:

```bash
# Docker
docker compose logs -f

# Manual
# Logs are output to stdout and logs/app.log
```

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
