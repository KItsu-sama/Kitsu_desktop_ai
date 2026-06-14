import asyncio
import sys
import traceback
from pathlib import Path
import os

# Ensure repo root is on sys.path so imports like `domain.*` resolve
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    os.environ.setdefault("PYTHONPATH", str(PROJECT_ROOT))

print('TEST: starting SLM provider import test')
try:
    from domain.ai.slm.provider import SLMProvider
except Exception as e:
    print('IMPORT_ERROR:', e)
    traceback.print_exc()
    sys.exit(1)

async def main():
    try:
        p = SLMProvider()
    except Exception as e:
        print('CONSTRUCT_ERROR:', e)
        traceback.print_exc()
        sys.exit(1)
    try:
        res = await p.infer_with_confidence('Hello test', context={})
        print('INFER_OK:', res)
    except Exception as e:
        print('INFER_ERROR:', e)
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
