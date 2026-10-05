from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    mode: str = 'demo'
    database: str = 'nabz-demo.sqlite3'
    cmc_key: str = ''
    monthly_limit: int = 13000
    external_credits: int = 0
    history_limit: int = 2000
    metadata_limit: int = 500
    market_interval: int = 600
    overview_interval: int = 1800
    translation_daily_limit: int = 100
    metadata_enabled: bool = False
    history_ids: tuple[int, ...] = ()
    history_access_confirmed: bool = False

    def validate(self):
        if self.mode not in {'demo', 'live'}:
            raise ValueError('APP_MODE must be demo or live')
        if self.mode == 'live' and (not self.cmc_key or self.cmc_key.startswith('replace')):
            raise ValueError('Live mode requires CMC_API_KEY on the server')
        if min(self.monthly_limit, self.history_limit, self.metadata_limit, self.translation_daily_limit) < 0:
            raise ValueError('Budgets cannot be negative')
        if self.external_credits < 0 or self.market_interval < 600 or self.overview_interval < 1800:
            raise ValueError('Invalid credits or polling interval below baseline')
        if len(self.history_ids) > 5 or any(i <= 0 for i in self.history_ids):
            raise ValueError('History allowlist supports at most five positive CMC IDs')
        if self.history_ids and not self.history_access_confirmed:
            raise ValueError('Confirm actual account history entitlement before enabling history IDs')

    @classmethod
    def from_env(cls):
        mode = os.getenv('APP_MODE', 'demo')
        return cls(mode=mode, database=os.getenv('DATABASE_PATH', f'nabz-{mode}.sqlite3'),
            cmc_key=os.getenv('CMC_API_KEY', ''), monthly_limit=int(os.getenv('MONTHLY_CREDIT_LIMIT', '13000')),
            external_credits=int(os.getenv('EXTERNAL_CREDITS', '0')),
            history_limit=int(os.getenv('HISTORY_CREDIT_LIMIT', '2000')),
            metadata_limit=int(os.getenv('METADATA_CREDIT_LIMIT', '500')),
            market_interval=int(os.getenv('MARKET_INTERVAL_SECONDS', '600')),
            overview_interval=int(os.getenv('OVERVIEW_INTERVAL_SECONDS', '1800')),
            translation_daily_limit=int(os.getenv('TRANSLATION_DAILY_LIMIT', '100')),
            metadata_enabled=os.getenv('CMC_METADATA_ENABLED') == 'true',
            history_ids=tuple(int(i.strip()) for i in os.getenv('CMC_HISTORY_IDS', '').split(',') if i.strip()),
            history_access_confirmed=os.getenv('CMC_HISTORY_ACCESS_CONFIRMED') == 'true')
