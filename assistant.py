import pvporcupine
import pyaudio
import numpy as np
import wave
import requests
import os
import time
import subprocess

# Nice way to load environment variables for deployments
from dotenv import load_dotenv
load_dotenv()

# Constants from .env
SILENCE_THRESHOLD = int(os.environ["SILENCE_THRESHOLD"])  # Adjust this threshold for silence detection
SILENCE_DURATION = float(os.environ["SILENCE_DURATION"])  # Duration in seconds to consider as silence
RECORDING_DURATION = int(os.environ["RECORDING_DURATION"])  # Maximum recording duration (in seconds)
WHISPERCPP_URL = os.environ["WHISPERCPP_URL"]
LLAMACPP_URL = os.environ["LLAMACPP_URL"]
SYSTEM_MESSAGE = os.environ["SYSTEM_MESSAGE"]
PROMPT_FORMAT = os.environ["PROMPT_FORMAT"]
STOP_TOKEN = os.environ["STOP_TOKEN"]
WAKEWORD = os.environ["WAKEWORD"]

SAMPLE_RATE = 16000  # Sample rate for the output WAV file, whisper.cpp likes this format
LLM_TEMP=0.1 # LLM should be a bit boring

# Initialize Porcupine with the PicoVoice key and wakeword
# The default wakeword is bumblebee
pv_key = os.environ["PV_KEY"]
porcupine = pvporcupine.create(access_key=pv_key, keywords=[WAKEWORD])
pa = pyaudio.PyAudio()

# Store the history of chat messages
history = []
MAX_HISTORY_SIZE = 5

# Set audio stream for wakeword detection
audio_stream = pa.open(
    rate=porcupine.sample_rate,
    channels=1,
    format=pyaudio.paInt16,
    input=True,
    frames_per_buffer=porcupine.frame_length)

# Submit the audio file to whisper.cpp
def whisper_api(file):
    # Whisper supports multiple files, but we're sending one
    files = {"file": file}
    
    # Required API call data
    api_data = {
        "temperature": "0.0",
        "response_format": "json"
    }

    # Call API and return text
    response = requests.post(WHISPERCPP_URL, data=api_data, files=files)
    return response.json()["text"]

def llama_api(prompt):
    # Format prompt before sending
    formatted_prompt = PROMPT_FORMAT.format(system=SYSTEM_MESSAGE, prompt=prompt)

    print(formatted_prompt)

    api_data = {
        "prompt": formatted_prompt,
        "n_predict": -1,
        "temperature": LLM_TEMP,
        "stop": [STOP_TOKEN],
        "tokens_cached": 0
    }

    response = requests.post(LLAMACPP_URL, headers={"Content-Type": "application/json"}, json=api_data)
    json_output = response.json()
    return json_output['content']

# Play a sound on wakeword
def play_wav_file(filename):
    subprocess.run(["aplay", filename])

def old_play(filename):    
    audio_stream = pa.open(
        rate=22050,
        channels=1,
        format=pyaudio.paInt16,
        output=True,
        frames_per_buffer=1024)

    with wave.open(filename, 'rb') as wf:
        data = wf.readframes(1024)
        while data:
            audio_stream.write(data)
            data = wf.readframes(1024)


# TTS using Piper and a custom onnx model
# TODO: Why is this a shell script?
def tts_piper(text):
    subprocess.run(["./tts.sh", text])

def add_to_history(item):
    history.append(item)  # Append the new item
    # Check if the list size exceeds 5
    if len(history) > MAX_HISTORY_SIZE:
        history.pop(0)  # Remove the oldest item (first element)

# Function to record audio and save it to a WAV file
def record_audio(filename):
    print("Recording...")
    frames = []
    silent_frames = 0
    start_time = time.time()
    silence_timer = None

    # Open a new audio stream for recording at the desired sample rate
    recording_stream = pa.open(
        rate=SAMPLE_RATE,
        channels=1,
        format=pyaudio.paInt16,
        output=False,
        input=True,
        frames_per_buffer=1024)

    while True:
        data = recording_stream.read(1024)
        audio_data = np.frombuffer(data, dtype=np.int16)
        frames.append(data)

        # Check for silence
        if np.abs(audio_data).mean() < SILENCE_THRESHOLD:
            if not silence_timer:
                silence_timer = time.time()
        else:
            silence_timer = None

        # Stop recording if silence is detected for a specified duration
        if silence_timer:
            if (time.time() - silence_timer) > SILENCE_DURATION:
                print("Silence detected")
                break

        talk_time = time.time() - start_time
        if talk_time > RECORDING_DURATION:
            print("Exceeded recording duration")
            break


    recording_stream.stop_stream()
    recording_stream.close()

    # Save the recorded audio to a WAV file
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bits
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b''.join(frames))

    # Call Whisper API to trancode
    transcript = ""
    with open(filename, "rb") as file:
        # Call whisper API to transcode file
        print("Transcribing...")
        transcript = whisper_api(file)
    
    # Trim the transcript
    transcript = transcript.strip()
    transcript = transcript.replace('\r', '')
    transcript = transcript.replace('\n', '')

    # Call LLM and get response but only if there's valid audio
    if transcript != "[BLANK_AUDIO]":
        # Sometimes we still get blank audio in the transcript, lets remove it
        transcript = transcript.replace("[BLANK_AUDIO]", "")

        # Read the assistant prompt from the config
        prompt = os.environ["ASSISTANT_PROMPT"].format(transcript=transcript, history="\n".join(history))

        # Add this to the his"tory up to the limit
        add_to_history("User: " + transcript)
        
        # Call LLM
        print("Calling LLM...")
        response = llama_api(prompt)
        add_to_history(F"{WAKEWORD}: " + response)
        # Text to speech output
        tts_piper(response)
    print(F"Listening. The wakeword is {WAKEWORD}..")

try:
    print(F"Listening. The wakeword is {WAKEWORD}..")
    while True:
        pcm = audio_stream.read(porcupine.frame_length)
        pcm = np.frombuffer(pcm, dtype=np.int16)
        keyword_index = porcupine.process(pcm)
        if keyword_index >= 0:
            print("Wake word detected!")
            play_wav_file("boing.wav")  # Play "boing.wav"
            record_audio("output.wav")  # Specify the filename for the output WAV file
finally:
    audio_stream.close()
    pa.terminate()
    porcupine.delete()
