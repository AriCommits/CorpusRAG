"""Tests for video configuration."""

from tools.video.config import VideoConfig


def test_from_dict_defaults():
    cfg = VideoConfig.from_dict({"llm": {}, "embedding": {}, "database": {}, "paths": {}})
    assert cfg.vision_model == "llava"
    assert cfg.scene_threshold == 0.3
    assert cfg.use_latex_fallback is True
    assert cfg.max_concurrent_jobs == 2
    assert cfg.context_window == 1
    assert cfg.audio_sample_rate == 16000
    assert cfg.audio_channels == 1
    assert cfg.keep_extracted_audio is False
    assert cfg.audio_timeout_seconds == 1800.0


def test_from_dict_audio_overrides():
    data = {
        "llm": {},
        "embedding": {},
        "database": {},
        "paths": {},
        "video": {
            "audio_sample_rate": 44100,
            "audio_channels": 2,
            "keep_extracted_audio": True,
        },
    }
    cfg = VideoConfig.from_dict(data)
    assert cfg.audio_sample_rate == 44100
    assert cfg.audio_channels == 2
    assert cfg.keep_extracted_audio is True


def test_from_dict_custom():
    data = {
        "llm": {},
        "embedding": {},
        "database": {},
        "paths": {},
        "video": {
            "vision_model": "moondream",
            "scene_threshold": 0.15,
            "context_window": 2,
            "max_concurrent_jobs": 4,
        },
    }
    cfg = VideoConfig.from_dict(data)
    assert cfg.vision_model == "moondream"
    assert cfg.scene_threshold == 0.15
    assert cfg.context_window == 2
    assert cfg.max_concurrent_jobs == 4


def test_from_dict_preserves_existing():
    data = {
        "llm": {},
        "embedding": {},
        "database": {},
        "paths": {},
        "video": {"whisper_model": "large-v2", "clean_model": "gemma4"},
    }
    cfg = VideoConfig.from_dict(data)
    assert cfg.whisper_model == "large-v2"
    assert cfg.clean_model == "gemma4"
    assert cfg.vision_model == "llava"  # default
