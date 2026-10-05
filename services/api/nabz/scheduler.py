import argparse
import logging
import time
from .config import Settings
from .providers import CmcProvider, DemoProvider, CapabilityUnavailable
from .store import Store, BudgetExceeded, now_iso
from .news import DemoNewsProvider, DemoTranslationProvider, RssProvider, ingest, translate_one, enqueue_current
from .translation import OpenAITranslationProvider


def tick_news(settings, store, news_provider, translator=None):
    if news_provider is None:
        return
    owner = store.acquire_job('news', 600)
    if owner:
        status = 'ready'
        try:
            count = ingest(store, news_provider.fetch(), model=translator.model if translator else None,
                prompt_version=getattr(translator, 'prompt_version', 'v1'))
            store.put('news_refresh', {'new_versions': count})
        except Exception:
            status = 'retry_pending'
        finally:
            store.finish_job('news', owner, 600, status)
    if translator is not None:
        enqueue_current(store, translator)
        for _ in range(10):
            if not translate_one(store, translator):
                break


def tick(settings, store, provider):
    """May be invoked by competing schedulers; durable leases and due times coalesce work."""
    jobs = {'market': settings.market_interval, 'overview': settings.overview_interval}
    # Indices are opt-in until account entitlement is confirmed.
    import os
    if settings.mode == 'live' and os.getenv('CMC_INDICES_ENABLED') == 'true':
        jobs.update(fear=3600, altcoin=3600)
    if settings.mode == 'live' and settings.metadata_enabled:
        jobs['metadata'] = 604800
    for name, interval in jobs.items():
        owner = store.acquire_job(name, interval)
        if owner is None:
            continue
        status = 'ready'
        try:
            if name == 'metadata':
                market = store.get('market')
                if not market or not market[0]:
                    raise ValueError('Market cache required for metadata')
                data = provider.fetch(name, ids=[c['id'] for c in market[0]])
            else:
                data = provider.fetch(name)
            fetched = now_iso()
            store.put(name, data, fetched)
            if name == 'metadata':
                store.put_metadata(data, fetched)
            if name == 'market' and settings.mode == 'live':
                store.snapshot_prices(data, fetched)
        except CapabilityUnavailable:
            status = 'unavailable'
        except BudgetExceeded:
            status = 'budget_exhausted'
        except Exception:
            # Do not log headers, payloads, URLs containing secrets or stack traces.
            status = 'retry_pending'
        finally:
            store.finish_job(name, owner, interval, status)
        logging.info('job=%s status=%s', name, status)


def tick_history(settings, store, provider):
    if settings.mode != 'live' or not settings.history_access_confirmed:
        return
    market = store.get('market')
    available = {c['id'] for c in market[0]} if market else set()
    for cmc_id in settings.history_ids:
        if cmc_id not in available:
            continue
        for chart_range in ['1d', '7d', '30d']:
            job = f'history:{cmc_id}:{chart_range}'
            owner = store.acquire_job(job, 21600)
            if not owner:
                continue
            status = 'ready'
            try:
                points = provider.fetch('history', cmc_id=cmc_id, chart_range=chart_range)
                store.put(f'chart:{cmc_id}:{chart_range}', points)
            except CapabilityUnavailable:
                status = 'unavailable'
            except BudgetExceeded:
                status = 'budget_exhausted'
            except Exception:
                status = 'retry_pending'
            finally:
                store.finish_job(job, owner, 21600, status)
            logging.info('job=%s status=%s', job, status)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    settings = Settings.from_env()
    settings.validate()
    store = Store(settings)
    provider = DemoProvider() if settings.mode == 'demo' else CmcProvider(settings, store)
    news_provider, translator = None, None
    if settings.mode == 'demo':
        news_provider, translator = DemoNewsProvider(), DemoTranslationProvider()
    else:
        import os
        urls = [u.strip() for u in os.getenv('NEWS_FEED_URLS', '').split(',') if u.strip()]
        if urls:
            news_provider = RssProvider(urls, os.getenv('NEWS_ALLOWED_DOMAINS', '').split(','),
                license_confirmed=os.getenv('NEWS_LICENSE_CONFIRMED') == 'true')
        translation_provider = os.getenv('TRANSLATION_PROVIDER', 'disabled')
        if translation_provider == 'openai':
            if os.getenv('NEWS_LICENSE_CONFIRMED') != 'true':
                raise ValueError('Translation requires confirmed source license')
            translator = OpenAITranslationProvider(store, api_key=os.getenv('TRANSLATION_API_KEY', ''),
                model=os.getenv('TRANSLATION_MODEL', ''), input_usd_per_million=os.getenv('TRANSLATION_INPUT_USD_PER_MILLION', '0'),
                output_usd_per_million=os.getenv('TRANSLATION_OUTPUT_USD_PER_MILLION', '0'),
                daily_limit_usd=os.getenv('TRANSLATION_DAILY_USD_LIMIT', '0'))
        elif translation_provider != 'disabled':
            raise ValueError('TRANSLATION_PROVIDER must be disabled or openai')
    logging.basicConfig(level=logging.INFO)
    while True:
        tick(settings, store, provider)
        tick_history(settings, store, provider)
        tick_news(settings, store, news_provider, translator)
        if args.once:
            return
        time.sleep(5)


if __name__ == '__main__':
    main()
