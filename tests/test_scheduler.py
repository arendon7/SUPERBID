from datetime import datetime,timezone,timedelta
from superbid_collector.scheduler import recommended_interval_seconds
def test_scheduler_far():assert recommended_interval_seconds(datetime.now(timezone.utc)+timedelta(days=2))==14400
def test_scheduler_near():assert recommended_interval_seconds(datetime.now(timezone.utc)+timedelta(minutes=10))==60
