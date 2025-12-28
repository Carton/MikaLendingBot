# Product Guidelines - Mika Lending Bot

## Communication & Logging
- **Professional & Informative:** The bot should provide clear, concise CLI logs focusing on financial transactions, lending offers, and system status to ensure transparency and trust.
- **Developer-Friendly Debugging:** Maintain detailed logging levels for strategy execution to facilitate troubleshooting during the Python 3 migration.

## Visual Identity & Web UI
- **Legacy Preservation:** For the web dashboard (`www/` components), maintain the original design and layout to ensure continuity for existing users.
- **Functional Clarity:** Prioritize data readability and layout stability in the web interface.

## Error Handling & Reliability
- **Resilient Operation:** The bot should prioritize resilience by attempting to retry connections and maintaining operation with fallback lending rates when API issues occur.
- **Comprehensive Logging:** All non-critical errors and system events should be silently recorded in logs to avoid unnecessary interruptions while providing a full audit trail.
- **Stable Defaults:** Ensure that default configurations lean towards safe, conservative lending behavior.
