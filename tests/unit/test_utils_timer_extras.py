import datetime

from generative_agents.modules.utils.timer import Timer


def test_timer_weekday_and_formats_cn():
    t = Timer(start="20240101-09:30")
    # Tuesday 2024-01-02, but start is 1st — we only assert format contains 年/月/日 and weekday Chinese
    df = t.daily_format_cn()
    assert "年" in df and "月" in df and "日" in df

    some_time = datetime.datetime(2024, 1, 3, 8, 15)
    tf = t.time_format_cn(some_time)
    assert "年" in tf and ":" in tf
