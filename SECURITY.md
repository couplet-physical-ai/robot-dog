# Security policy

Report vulnerabilities privately through [GitHub private vulnerability reporting](https://github.com/couplet-physical-ai/robot-dog/security/advisories/new), not a public issue. Include only sanitized, non-actuating reproduction details. A potential physical safety issue requires stopping the operation and notifying its qualified operator; a software stop command is not a certified emergency stop.

Never commit secrets, credentials, unit serials, MAC/IP addresses, identifying hostnames, GPS/location data, raw telemetry, robot captures, or private logs. Use synthetic fixtures and keep target-specific intake records outside the repository. The default fake and tests must not connect to a robot or load optional SDK transports. Changes to robot-facing controls require an independent safety review. See [safety policy](docs/safety/safety-policy.md) and [third-party software ledger](docs/third-party.md).
