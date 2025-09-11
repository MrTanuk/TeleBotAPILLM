import logging
import io
import speech_recognition as sr
from pydub import AudioSegment

logger = logging.getLogger(__name__)


def speech(ogg_bytes):
    audio = AudioSegment.from_ogg(io.BytesIO(ogg_bytes))

    audio = audio.set_frame_rate(16000).set_channels(1)

    wav_bytes = io.BytesIO()
    audio.export(wav_bytes, format="wav")
    wav_bytes.seek(0)

    r = sr.Recognizer()

    try:
        with sr.AudioFile(wav_bytes) as source:
            r.adjust_for_ambient_noise(source)
            audio_data = r.record(source)

        text = r.recognize_google(audio_data, language="es-ES")
        return text
    except sr.UnknownValueError:
        return "Could not understand audio"
    except sr.RequestError as e:
        return f"Error connecting to the recognition service: {e}"
    finally:
        wav_bytes.close()
