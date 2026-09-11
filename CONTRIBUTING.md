# Contributing

Contributions are welcome through an issue or pull request.

## Development gate

1. Create a virtual environment and install `requirements.txt`.
2. Keep all environment values in ignored `.env`; never commit credentials, private keys, account identifiers, customer IDs, or generated data.
3. Add or update tests with behavioral changes.
4. Run:

   ```powershell
   python -m pytest -q
   python -m compileall -q generators snowflake_source validation infra tools
   python tools\security_scan.py --working-tree --git-history
   ```

5. Update documentation and evidence status. Local tests must never be presented as a live deployment result.

## Pull requests

Keep changes focused, explain product assumptions, cite current official Microsoft/Snowflake documentation for behavior changes, and call out any operation that can recreate a mirror, reseed data, expand privileges, or delete POC objects.

Do not include customer screenshots, tenant metadata, Fabric/Snowflake identifiers, query/run URLs, or copied production schemas.
