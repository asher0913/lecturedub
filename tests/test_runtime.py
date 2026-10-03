from types import SimpleNamespace

from lecturedub.asr import phrases_from_timestamps, transcribe_to_srt
from lecturedub.runtime import CUDA_TTS, MLX_TTS, backend, default_llm, default_tts


def test_this_mac_uses_mlx(monkeypatch):
    monkeypatch.delenv("LECTUREDUB_BACKEND", raising=False)
    assert backend() == "mlx"
    assert default_tts() == MLX_TTS
    assert "mlx-community" in default_llm()


def test_backend_override(monkeypatch):
    monkeypatch.setenv("LECTUREDUB_BACKEND", "cuda")
    assert backend() == "cuda"
    assert default_tts() == CUDA_TTS
    assert default_llm() == "Qwen/Qwen3-8B"


def test_phrases_accept_aligner_items():
    stamps = SimpleNamespace(
        items=[
            SimpleNamespace(text="Hello", start_time=0.0, end_time=0.3),
            SimpleNamespace(text="there.", start_time=0.4, end_time=0.8),
        ]
    )
    cues = phrases_from_timestamps(stamps)
    assert cues[0].text == "Hello there."


def test_phrases_group_words_into_sentences():
    stamps = [
        SimpleNamespace(text="Hello", start_time=0.0, end_time=0.3),
        SimpleNamespace(text="there.", start_time=0.4, end_time=0.8),
        SimpleNamespace(text="Next", start_time=2.0, end_time=2.3),
        SimpleNamespace(text="point.", start_time=2.4, end_time=2.8),
    ]
    cues = phrases_from_timestamps(stamps, offset=10)
    assert [cue.text for cue in cues] == ["Hello there.", "Next point."]
    assert cues[0].start == 10
    assert cues[1].start == 12


def _write_three_cues(path, title, model_id):
    path.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nHello there.\n\n"
        "2\n00:00:01,100 --> 00:00:02,000\nThis is Raft.\n\n"
        "3\n00:00:02,200 --> 00:00:03,000\nNext point.\n",
        encoding="utf-8",
    )


def test_transcribe_uses_mlx_on_apple(monkeypatch, tmp_path):
    monkeypatch.delenv("LECTUREDUB_BACKEND", raising=False)
    wav = tmp_path / "audio.wav"
    wav.write_bytes(b"x" * 2000)
    srt = tmp_path / "out.srt"
    seen = {}

    def fake(wav_path, srt_path, *, title, model_id):
        seen["backend"] = "mlx"
        seen["model"] = model_id
        _write_three_cues(srt_path, title, model_id)

    monkeypatch.setattr("lecturedub.asr._transcribe_mlx", fake)
    monkeypatch.setattr("lecturedub.asr._transcribe_cuda", lambda *args, **kwargs: seen.setdefault("cuda", True))
    transcribe_to_srt(tmp_path / "video.mp4", srt, title="cs425", work_wav=wav)
    assert seen == {"backend": "mlx", "model": "Qwen/Qwen3-ASR-1.7B"}
    assert "Raft" in srt.read_text(encoding="utf-8")


def test_transcribe_uses_cuda_when_selected(monkeypatch, tmp_path):
    monkeypatch.setenv("LECTUREDUB_BACKEND", "cuda")
    wav = tmp_path / "audio.wav"
    wav.write_bytes(b"x" * 2000)
    srt = tmp_path / "out.srt"
    seen = {}

    def fake(wav_path, srt_path, *, title, model_id):
        seen["backend"] = "cuda"
        seen["model"] = model_id
        seen["title"] = title
        _write_three_cues(srt_path, title, model_id)

    monkeypatch.setattr("lecturedub.asr._transcribe_cuda", fake)
    transcribe_to_srt(tmp_path / "video.mp4", srt, title="lecture", work_wav=wav)
    assert seen["backend"] == "cuda"
    assert seen["model"] == "Qwen/Qwen3-ASR-1.7B"
    assert seen["title"] == "lecture"
    assert "Next point." in srt.read_text(encoding="utf-8")


def test_phrases_split_on_a_long_pause():
    stamps = [
        {"text": "kept", "start_time": 0.0, "end_time": 0.3},
        {"text": "apart", "start_time": 2.0, "end_time": 2.3},
    ]
    cues = phrases_from_timestamps(stamps)
    assert [cue.text for cue in cues] == ["kept", "apart"]
