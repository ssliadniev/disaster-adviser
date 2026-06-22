from typing import Iterable, Optional

import aiohttp
from aiostream import pipe, stream

from app.contracts.disaster import DedupKey, dedup_key
from app.modules.disaster_scanner.config import ScannerConfig
from app.modules.disaster_scanner.core import try_normalize
from app.modules.disaster_scanner.operators import distinct
from app.modules.disaster_scanner.sources_auth import TokenProvider
from app.modules.disaster_scanner.streams import (fetch_disasteraware_stream,
                                                  fetch_nasa_stream)


def build_disaster_pipeline(
    session: aiohttp.ClientSession,
    token_provider: TokenProvider,
    config: ScannerConfig,
    *,
    initial_keys: Optional[Iterable[DedupKey]] = None,
):
    nasa = fetch_nasa_stream(session, config)
    dae = fetch_disasteraware_stream(session, token_provider, config)

    return (
        stream.merge(nasa, dae)
        | pipe.map(try_normalize)
        | pipe.filter(lambda event: event is not None)
        | distinct.pipe(
            key=dedup_key,
            max_size=config.dedup_max_size,
            initial_keys=initial_keys,
        )
    )
