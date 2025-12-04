import logging
import io
import speech_recognition as sr
from pydub import AudioSegment

logger = logging.getLogger(__name__)

def speech(ogg_bytes):
    """
    Converts OGG bytes (from Telegram) to text.
    
    Note: This is a BLOCKING function (CPU bound + Synchronous Network request).
    It must be run in a separate thread.
    """
    try:
        # 1. Convert OGG (Telegram) to WAV (Compatible with SpeechRecognition)
        # Pydub handles bytes in memory
        audio = AudioSegment.from_ogg(io.BytesIO(ogg_bytes))
        
        # Adjust for better recognition (16kHz mono is standard for voice)
        audio = audio.set_frame_rate(16000).set_channels(1)

        wav_bytes = io.BytesIO()
        audio.export(wav_bytes, format="wav")
        wav_bytes.seek(0)

        # 2. Recognition process
        r = sr.Recognizer()
        with sr.AudioFile(wav_bytes) as source:
            # Optional: Calibrate ambient noise briefly
            # r.adjust_for_ambient_noise(source, duration=0.5) 
            audio_data = r.record(source)

        # Call to Google API (Free/Limited)
        # Using "es-ES" as default, you might want to change this to "en-US" or make it dynamic
        text = r.recognize_google(audio_data, language="en-US") 
        return text

    except sr.UnknownValueError:
        return None # Audio could not be understood
    except sr.RequestError as e:
        logger.error(f"SpeechRecognition service error: {e}")
        raise RuntimeError("Error connecting to speech service.")
    except Exception as e:
        logger.error(f"Error processing audio: {e}", exc_info=True)
        raise e
    finally:
        # Explicitly close the byte buffer (good practice)
        if 'wav_bytes' in locals():
            wav_bytes.close()
