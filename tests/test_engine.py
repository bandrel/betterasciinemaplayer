from bettercast.engine import PlaybackEngine


class TestEngineInit:
    def test_initial_state(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        assert engine.position == 0.0
        assert engine.speed == 1.0
        assert engine.playing is False
        assert engine.duration == 4.0

    def test_screen_dimensions(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        assert engine.screen.columns == 80
        assert engine.screen.lines == 24


class TestEngineSeek:
    def test_seek_to_start(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(0.0)
        assert engine.position == 0.0
        assert engine.screen.display[0].strip() == ""

    def test_seek_to_middle(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(2.0)
        assert engine.position == 2.0
        assert "echo hello" in engine.screen.display[0]
        assert engine.screen.display[1].strip() == "hello"
        assert engine.screen.display[2].startswith("$ ")

    def test_seek_to_end(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(4.0)
        assert engine.position == 4.0
        assert "Python 3.12.0" in engine.screen.display[3]
        assert engine.screen.display[4].startswith("$ ")

    def test_seek_clamps_to_zero(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(-5.0)
        assert engine.position == 0.0

    def test_seek_clamps_to_duration(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(100.0)
        assert engine.position == 4.0

    def test_seek_resets_screen(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.seek(4.0)
        assert "Python" in engine.screen.display[3]
        engine.seek(0.0)
        assert engine.screen.display[3].strip() == ""


class TestEngineAdvance:
    def test_advance_while_paused_returns_false(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        assert engine.advance(1.0) is False
        assert engine.position == 0.0

    def test_advance_applies_events(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        changed = engine.advance(1.0)
        assert changed is True
        assert engine.position == 1.0
        assert "$ " in engine.screen.display[0]

    def test_advance_respects_speed(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        engine.speed = 2.0
        engine.advance(1.0)
        assert engine.position == 2.0
        assert "echo hello" in engine.screen.display[0]

    def test_advance_pauses_at_end(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        engine.advance(10.0)
        assert engine.playing is False
        assert engine.position == 4.0

    def test_advance_returns_false_when_no_events(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        engine.seek(4.0)
        engine.playing = True
        changed = engine.advance(1.0)
        assert changed is False


class TestEngineControls:
    def test_play(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.play()
        assert engine.playing is True

    def test_pause(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.playing = True
        engine.pause()
        assert engine.playing is False

    def test_toggle(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.toggle()
        assert engine.playing is True
        engine.toggle()
        assert engine.playing is False

    def test_set_speed(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.set_speed(2.0)
        assert engine.speed == 2.0

    def test_set_speed_clamps_low(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.set_speed(0.1)
        assert engine.speed == 0.5

    def test_set_speed_clamps_high(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.set_speed(20.0)
        assert engine.speed == 8.0


class TestEngineSearch:
    def test_build_search_index(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        assert len(engine._search_index) > 0

    def test_search_index_deduplicates(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        texts = [text for _, text in engine._search_index]
        assert len(texts) == len(set(texts))

    def test_next_match_finds_text(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 0.0
        match_time = engine.next_match("python")
        assert match_time is not None
        assert match_time >= 3.0

    def test_next_match_case_insensitive(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 0.0
        match_time = engine.next_match("HELLO")
        assert match_time is not None
        assert match_time >= 1.0

    def test_next_match_returns_none_past_end(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 4.0
        assert engine.next_match("hello") is None

    def test_prev_match_finds_text(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 4.0
        match_time = engine.prev_match("hello")
        assert match_time is not None
        assert match_time < 4.0

    def test_prev_match_returns_none_at_start(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        engine.position = 0.0
        assert engine.prev_match("hello") is None

    def test_next_match_empty_query_returns_none(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        assert engine.next_match("") is None

    def test_count_matches(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        count = engine.count_matches("python")
        assert count >= 1

    def test_count_matches_empty_query(self, sample_recording):
        engine = PlaybackEngine(sample_recording)
        engine.build_search_index()
        assert engine.count_matches("") == 0
