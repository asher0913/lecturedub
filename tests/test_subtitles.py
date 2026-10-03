from lecturedub.subtitles import group_cues, parse_subtitles, speakable_units

RAW = """1
00:00:01,000 --> 00:00:02,200
Hello there.

2
00:00:02,300 --> 00:00:04,000
This is Raft.

3
00:00:08,000 --> 00:00:09,000
[Music]

4
00:01:10.500 --> 00:01:12.000
Next point.
"""


def test_parse_and_group():
    cues = parse_subtitles(RAW)
    assert [cue.text for cue in cues] == ["Hello there.", "This is Raft.", "Next point."]
    grouped = group_cues(cues, min_seconds=1.0, max_seconds=8.0, gap_seconds=0.8)
    assert len(grouped) == 2
    assert "Raft" in grouped[0].text
    assert grouped[1].start > 60


def test_speakable_units():
    assert speakable_units("副本复制 Raft") == 4 + 2
