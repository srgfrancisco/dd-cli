"""Tests for watch_loop utility."""

from unittest.mock import Mock, patch

from ddogctl.utils.watch import watch_loop


def test_watch_loop_calls_render_func():
    """Test that watch_loop calls the render function at least once."""
    render_func = Mock(return_value="test output")

    # Make time.sleep raise KeyboardInterrupt to exit the loop after first iteration
    with patch("ddogctl.utils.watch.time.sleep", side_effect=KeyboardInterrupt):
        watch_loop(render_func, interval=30)

    render_func.assert_called_once()


def test_watch_loop_uses_live_display():
    """Test that watch_loop uses Rich Live for display."""
    render_func = Mock(return_value="test output")

    with patch("ddogctl.utils.watch.time.sleep", side_effect=KeyboardInterrupt):
        with patch("ddogctl.utils.watch.Live") as mock_live_class:
            mock_live = Mock()
            mock_live_class.return_value.__enter__ = Mock(return_value=mock_live)
            mock_live_class.return_value.__exit__ = Mock(return_value=False)

            watch_loop(render_func, interval=30)

            # Verify Live.update was called with render output
            mock_live.update.assert_called_once_with("test output")


def test_watch_loop_sleeps_for_interval():
    """Test that watch_loop sleeps for the specified interval."""
    render_func = Mock(return_value="test output")

    with patch("ddogctl.utils.watch.time.sleep", side_effect=KeyboardInterrupt) as mock_sleep:
        watch_loop(render_func, interval=10)

    mock_sleep.assert_called_once_with(10)


def test_watch_loop_default_interval():
    """Test that watch_loop defaults to 30 second interval."""
    render_func = Mock(return_value="test output")

    with patch("ddogctl.utils.watch.time.sleep", side_effect=KeyboardInterrupt) as mock_sleep:
        watch_loop(render_func)

    mock_sleep.assert_called_once_with(30)


def test_watch_loop_handles_keyboard_interrupt():
    """Test that watch_loop exits cleanly on KeyboardInterrupt."""
    render_func = Mock(return_value="test output")

    with patch("ddogctl.utils.watch.time.sleep", side_effect=KeyboardInterrupt):
        # Should not raise an exception
        watch_loop(render_func, interval=5)


def test_watch_loop_multiple_iterations():
    """Test that watch_loop calls render_func on each iteration."""
    render_func = Mock(return_value="test output")
    call_count = 0

    def sleep_side_effect(interval):
        nonlocal call_count
        call_count += 1
        if call_count >= 3:
            raise KeyboardInterrupt
        return None

    with patch("ddogctl.utils.watch.time.sleep", side_effect=sleep_side_effect):
        watch_loop(render_func, interval=5)

    # Should be called 3 times (initial + 2 more before KeyboardInterrupt on 3rd sleep)
    assert render_func.call_count == 3


def test_watch_loop_clamps_minimum_interval():
    """Test that watch_loop clamps interval to minimum 1 second."""
    render_func = Mock(return_value="test output")

    with patch("ddogctl.utils.watch.time.sleep", side_effect=KeyboardInterrupt) as mock_sleep:
        watch_loop(render_func, interval=0)

    mock_sleep.assert_called_once_with(1)


def test_watch_loop_accepts_custom_console():
    """Test that watch_loop accepts a custom console."""
    render_func = Mock(return_value="test output")
    custom_console = Mock()

    with patch("ddogctl.utils.watch.time.sleep", side_effect=KeyboardInterrupt):
        with patch("ddogctl.utils.watch.Live") as mock_live_class:
            mock_live = Mock()
            mock_live_class.return_value.__enter__ = Mock(return_value=mock_live)
            mock_live_class.return_value.__exit__ = Mock(return_value=False)

            watch_loop(render_func, interval=30, console=custom_console)

            mock_live_class.assert_called_once()
            call_kwargs = mock_live_class.call_args
            assert call_kwargs[1]["console"] == custom_console
