import asyncio

from nobleport.voice import VoiceSettings, VoiceboxSpeaker


def test_voicebox_speaker_disabled_is_fail_open():
    settings = VoiceSettings(
        enabled=False,
        base_url="http://127.0.0.1:17493",
        profile="Stephanie",
        client_id="stephanie-ai",
        personality=False,
        timeout_seconds=1.0,
    )
    speaker = VoiceboxSpeaker(settings)

    result = asyncio.run(speaker.speak("Hello from Stephanie."))

    assert result["spoken"] is False
    assert result["reason"] == "disabled"
    assert result["provider"] == "voicebox"


def test_voicebox_summary_does_not_expose_endpoint():
    settings = VoiceSettings(
        enabled=True,
        base_url="http://voicebox.internal:17493",
        profile="Stephanie",
        client_id="stephanie-ai",
        personality=True,
        timeout_seconds=1.0,
    )
    speaker = VoiceboxSpeaker(settings)

    summary = speaker.summary()

    assert summary == {
        "provider": "voicebox",
        "enabled": True,
        "profile_configured": True,
    }
    assert "base_url" not in summary
