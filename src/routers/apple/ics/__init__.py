import logging
from datetime import datetime, timedelta

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from ics import Calendar, Event
from ics.alarm.display import DisplayAlarm

router = APIRouter(tags=['Utils'], prefix='/apple')

logger = logging.getLogger(__file__)


@router.get('/ics/calander', summary='Apple日历订阅示例')
def calander():
    tomorrow = datetime.now() + timedelta(days=1)
    c = Calendar()
    e = Event()
    e.name = 'My cool event'
    e.description = 'A meaningful description'
    e.begin = tomorrow.replace(hour=4, minute=0, second=0, microsecond=0)
    e.end = tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
    e.alarms = [DisplayAlarm(timedelta(minutes=-10))]
    c.events.add(e)

    return PlainTextResponse(c.serialize())
