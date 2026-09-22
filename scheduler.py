import time
import traceback

from apscheduler.schedulers.blocking import BlockingScheduler

from config import settings
import runner


def scheduled_symbols():
    raw = (settings.schedule_symbols or "ALL").strip().upper()

    if raw in {"", "ALL", "*"}:
        return list(settings.symbol_queries.keys())

    return [item.strip() for item in raw.split(",") if item.strip()]


def scheduled_timeframes():
    raw = (settings.schedule_timeframes or "1h,4h").strip().lower()

    return [
        tf.strip()
        for tf in raw.split(",")
        if tf.strip() in runner.TF
    ]


def send_or_print(text):
    if settings.telegram_token and settings.telegram_chat_id:
        try:
            runner.send(text)
            return
        except Exception as exc:
            print("Telegram failed:", exc)

    print(text)


def run_timeframe(timeframe):
    if timeframe not in runner.TF:
        return

    for symbol in scheduled_symbols():
        try:
            report = runner.analyze(symbol, timeframe, days=settings.default_days)
            send_or_print(runner.report_text(report))
        except Exception as exc:
            msg = f"Schedule error: {symbol} {timeframe}: {exc}"
            print(msg)
            traceback.print_exc()

            try:
                send_or_print(msg)
            except Exception:
                pass

        time.sleep(max(settings.request_sleep, 0.25))


def run_1h():
    if "1h" in scheduled_timeframes():
        run_timeframe("1h")


def run_4h():
    if "4h" in scheduled_timeframes():
        run_timeframe("4h")


def run_daily_open():
    run_timeframe("1d")


def run_daily_close():
    run_timeframe("1d")


def run_weekly():
    run_timeframe("1d")


if __name__ == "__main__":
    sched = BlockingScheduler(timezone="UTC")

    sched.add_job(
        run_1h,
        "cron",
        minute=2,
        id="hourly",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    sched.add_job(
        run_4h,
        "cron",
        hour="*/4",
        minute=4,
        id="four_hour",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    sched.add_job(
        run_daily_open,
        "cron",
        hour=0,
        minute=5,
        id="daily_open",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    sched.add_job(
        run_daily_close,
        "cron",
        hour=23,
        minute=55,
        id="daily_close",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    sched.add_job(
        run_weekly,
        "cron",
        day_of_week="mon",
        hour=0,
        minute=10,
        id="weekly",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    print("Deriv Research Desk scheduler running in UTC.")
    print("Symbols:", ", ".join(scheduled_symbols()))
    print("Periodic timeframes:", ", ".join(scheduled_timeframes()))

    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        pass
