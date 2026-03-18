"""
Camera FPS Test
===============
Measures the actual frame rate of connected cameras.
Tests both the reported FPS (from driver) and the real measured FPS.
"""
import cv2
import time
import sys


def test_camera_fps(device_index: int = 0, test_duration: float = 5.0,
                    resolutions: list = None):
    """
    Test actual FPS of a camera at different resolutions.
    
    Args:
        device_index: Camera index (0 = first camera)
        test_duration: How long to capture frames for measurement (seconds)
        resolutions: List of (width, height) tuples to test
    """
    if resolutions is None:
        resolutions = [
            (640, 480),
            (1280, 720),
        ]

    print(f"{'=' * 60}")
    print(f"  Camera FPS Test — Device {device_index}")
    print(f"  Test duration: {test_duration}s per resolution")
    print(f"{'=' * 60}\n")

    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        print(f"[ERROR] Could not open camera {device_index}")
        return

    # Show camera backend info
    backend = cap.getBackendName()
    print(f"  Backend: {backend}\n")

    for width, height in resolutions:
        print(f"--- Testing {width}x{height} ---")

        # Set resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, 30)

        # Read a warm-up frame
        for _ in range(5):
            cap.read()

        # Check what the driver reports
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        reported_fps = cap.get(cv2.CAP_PROP_FPS)
        print(f"  Requested:    {width}x{height} @ 30 FPS")
        print(f"  Driver says:  {actual_w}x{actual_h} @ {reported_fps:.1f} FPS")

        # Measure real FPS
        frame_count = 0
        frame_times = []
        start = time.perf_counter()

        while True:
            ret, frame = cap.read()
            now = time.perf_counter()

            if not ret:
                print(f"  [WARNING] Frame read failed at frame {frame_count}")
                break

            frame_times.append(now)
            frame_count += 1

            if (now - start) >= test_duration:
                break

        elapsed = frame_times[-1] - frame_times[0] if len(frame_times) > 1 else 0

        if elapsed > 0 and frame_count > 1:
            real_fps = (frame_count - 1) / elapsed
            avg_interval_ms = (elapsed / (frame_count - 1)) * 1000

            # Calculate jitter (standard deviation of frame intervals)
            intervals = [frame_times[i+1] - frame_times[i]
                         for i in range(len(frame_times) - 1)]
            import statistics
            if len(intervals) > 1:
                jitter_ms = statistics.stdev(intervals) * 1000
            else:
                jitter_ms = 0.0

            print(f"  Measured FPS: {real_fps:.2f}")
            print(f"  Total frames: {frame_count} in {elapsed:.2f}s")
            print(f"  Avg interval: {avg_interval_ms:.1f} ms")
            print(f"  Jitter (σ):   {jitter_ms:.1f} ms")

            # Min/Max intervals
            min_interval = min(intervals) * 1000
            max_interval = max(intervals) * 1000
            print(f"  Min interval: {min_interval:.1f} ms")
            print(f"  Max interval: {max_interval:.1f} ms")
        else:
            print(f"  [ERROR] Not enough frames captured ({frame_count})")

        print()

    cap.release()

    print(f"{'=' * 60}")
    print(f"  Test complete")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    device = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    test_camera_fps(device_index=device, test_duration=duration)
