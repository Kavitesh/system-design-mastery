"""
Real-Time Stream Processor with Windowing
==========================================
Simulates a stream of events and processes them using tumbling and
sliding windows. Demonstrates event-time processing and late data handling.
"""

import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
#   Event generation
# ---------------------------------------------------------------------------

@dataclass
class Event:
    user_id: str
    action: str
    value: float
    event_time: datetime
    arrival_time: datetime = None

    def __post_init__(self):
        if self.arrival_time is None:
            self.arrival_time = self.event_time


ACTIONS = ["click", "purchase", "view", "add_to_cart"]

def generate_event_stream(n=80, base_time=None):
    """Generate a stream of events with some arriving late."""
    base = base_time or datetime(2025, 3, 15, 10, 0, 0)
    events = []
    for _ in range(n):
        event_time = base + timedelta(seconds=random.randint(0, 300))

        # 15% of events arrive late (1-30 seconds of delay)
        if random.random() < 0.15:
            delay = timedelta(seconds=random.randint(1, 30))
            arrival_time = event_time + delay
        else:
            arrival_time = event_time + timedelta(milliseconds=random.randint(10, 200))

        events.append(Event(
            user_id=f"user_{random.randint(1, 10)}",
            action=random.choice(ACTIONS),
            value=round(random.uniform(1, 100), 2),
            event_time=event_time,
            arrival_time=arrival_time,
        ))

    return sorted(events, key=lambda e: e.arrival_time)


# ---------------------------------------------------------------------------
#   Window definitions
# ---------------------------------------------------------------------------

@dataclass
class WindowResult:
    window_start: datetime
    window_end: datetime
    event_count: int
    total_value: float
    actions: dict = field(default_factory=dict)


def get_tumbling_window(event_time, window_size_seconds):
    """Assign event to a fixed, non-overlapping window."""
    epoch = event_time.timestamp()
    window_start_epoch = (epoch // window_size_seconds) * window_size_seconds
    start = datetime.fromtimestamp(window_start_epoch)
    end = start + timedelta(seconds=window_size_seconds)
    return start, end


def get_sliding_windows(event_time, window_size_seconds, slide_seconds):
    """Assign event to all overlapping sliding windows it belongs to."""
    windows = []
    epoch = event_time.timestamp()
    earliest_start = (epoch // slide_seconds) * slide_seconds - window_size_seconds + slide_seconds
    t = earliest_start
    while t <= epoch:
        start = datetime.fromtimestamp(t)
        end = start + timedelta(seconds=window_size_seconds)
        if start <= event_time < end:
            windows.append((start, end))
        t += slide_seconds
    return windows


# ---------------------------------------------------------------------------
#   Stream processor
# ---------------------------------------------------------------------------

class StreamProcessor:
    def __init__(self, watermark_delay_seconds=10):
        self.watermark_delay = timedelta(seconds=watermark_delay_seconds)
        self.watermark = None
        self.late_events = 0
        self.processed_events = 0

    def process_tumbling(self, events, window_seconds=60):
        """Process events using tumbling (fixed) windows."""
        windows = defaultdict(lambda: {"count": 0, "value": 0.0, "actions": defaultdict(int)})

        for event in events:
            self._update_watermark(event.arrival_time)

            if self.watermark and event.event_time < self.watermark - self.watermark_delay:
                self.late_events += 1
                continue

            start, end = get_tumbling_window(event.event_time, window_seconds)
            key = (start, end)
            windows[key]["count"] += 1
            windows[key]["value"] += event.value
            windows[key]["actions"][event.action] += 1
            self.processed_events += 1

        results = []
        for (start, end), data in sorted(windows.items()):
            results.append(WindowResult(
                window_start=start,
                window_end=end,
                event_count=data["count"],
                total_value=round(data["value"], 2),
                actions=dict(data["actions"]),
            ))
        return results

    def process_sliding(self, events, window_seconds=120, slide_seconds=60):
        """Process events using sliding (overlapping) windows."""
        windows = defaultdict(lambda: {"count": 0, "value": 0.0, "actions": defaultdict(int)})

        for event in events:
            self._update_watermark(event.arrival_time)

            if self.watermark and event.event_time < self.watermark - self.watermark_delay:
                self.late_events += 1
                continue

            event_windows = get_sliding_windows(
                event.event_time, window_seconds, slide_seconds
            )
            for start, end in event_windows:
                key = (start, end)
                windows[key]["count"] += 1
                windows[key]["value"] += event.value
                windows[key]["actions"][event.action] += 1
            self.processed_events += 1

        results = []
        for (start, end), data in sorted(windows.items()):
            results.append(WindowResult(
                window_start=start,
                window_end=end,
                event_count=data["count"],
                total_value=round(data["value"], 2),
                actions=dict(data["actions"]),
            ))
        return results

    def _update_watermark(self, arrival_time):
        if self.watermark is None or arrival_time > self.watermark:
            self.watermark = arrival_time


# ---------------------------------------------------------------------------
#   Display helpers
# ---------------------------------------------------------------------------

def print_window_results(results, title):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")
    print(f"  {'Window':<30} {'Events':>7} {'Value ($)':>10}  Top Action")
    print(f"  {'-'*30} {'-'*7} {'-'*10}  {'-'*15}")

    for w in results:
        start_str = w.window_start.strftime("%H:%M:%S")
        end_str = w.window_end.strftime("%H:%M:%S")
        top_action = max(w.actions, key=w.actions.get) if w.actions else "-"
        top_count = w.actions.get(top_action, 0)
        print(f"  [{start_str} - {end_str}]         {w.event_count:>7} "
              f"{w.total_value:>10,.2f}  {top_action} ({top_count})")


# ---------------------------------------------------------------------------
#   Demo
# ---------------------------------------------------------------------------

def main():
    print("Stream Processor with Windowing Demo")

    random.seed(42)
    events = generate_event_stream(80)

    print(f"\nGenerated {len(events)} events")
    late_count = sum(
        1 for e in events
        if (e.arrival_time - e.event_time).total_seconds() > 1
    )
    print(f"Late-arriving events: {late_count}")
    time_span = events[-1].event_time - events[0].event_time
    print(f"Time span: {time_span.total_seconds():.0f} seconds")

    # Tumbling windows - 60 second windows, no overlap
    proc1 = StreamProcessor(watermark_delay_seconds=10)
    tumbling_results = proc1.process_tumbling(events, window_seconds=60)
    print_window_results(tumbling_results, "Tumbling Windows (60s, no overlap)")
    print(f"\n  Processed: {proc1.processed_events} | "
          f"Late (dropped): {proc1.late_events}")

    # Sliding windows - 120 second window, 60 second slide
    proc2 = StreamProcessor(watermark_delay_seconds=10)
    sliding_results = proc2.process_sliding(
        events, window_seconds=120, slide_seconds=60
    )
    print_window_results(sliding_results, "Sliding Windows (120s window, 60s slide)")
    print(f"\n  Processed: {proc2.processed_events} | "
          f"Late (dropped): {proc2.late_events}")

    # Comparison
    print(f"\n{'='*65}")
    print("  Comparison")
    print(f"{'='*65}")
    print(f"  Tumbling windows produced:  {len(tumbling_results)} windows")
    print(f"  Sliding windows produced:   {len(sliding_results)} windows")
    print(f"\n  Tumbling windows are non-overlapping - each event appears in")
    print(f"  exactly one window. Sliding windows overlap - a single event")
    print(f"  can appear in multiple windows, giving smoother aggregations.")


if __name__ == "__main__":
    main()
