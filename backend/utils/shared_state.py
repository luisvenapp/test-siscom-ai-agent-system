from typing import Dict
from asyncio import Future

pending_responses: Dict[str, Future] = {}