import os
import json
import asyncio
from pathlib import Path

from crawlers.hkma import HKMACrawler
from crawlers.mas import MASCrawler
from crawlers.finma import FINMACrawler


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


async def _run_all() -> None:
    out_dir = Path(os.getenv("CRAWLER_OUTPUT_DIR", "tests/crawlers/output")).resolve()
    _ensure_dir(out_dir)

    hkma = HKMACrawler()
    mas = MASCrawler()
    finma = FINMACrawler()

    hkma_data, mas_data, finma_data = await asyncio.gather(
        hkma.crawl(), mas.crawl(), finma.crawl()
    )

    def write_jsonl(filename: str, items):
        p = out_dir / filename
        with p.open("w", encoding="utf-8") as f:
            for it in (items or []):
                f.write(json.dumps(it, default=str) + "\n")
        return p

    hkma_path = write_jsonl("hkma.jsonl", hkma_data)
    mas_path = write_jsonl("mas.jsonl", mas_data)
    finma_path = write_jsonl("finma.jsonl", finma_data)

    print("Saved outputs:")
    print(f"- HKMA:  {len(hkma_data)} -> {hkma_path}")
    print(f"- MAS:   {len(mas_data)} -> {mas_path}")
    print(f"- FINMA: {len(finma_data)} -> {finma_path}")


if __name__ == "__main__":
    # Environment toggles (optional):
    # - CRAWLER_ONLINE_ONLY=true
    # - CRAWLER_USE_DOWNLOADS=true
    # - CRAWLER_DOWNLOADS_DIR=./crawler_downloads
    # - CRAWLER_OUTPUT_DIR=tests/crawlers/output
    asyncio.run(_run_all())

