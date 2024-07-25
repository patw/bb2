# Bumblebee2

Bumblebee2 is an LLM driven home assistant.  Say the wake word "bumblebee" and ask any question you want to a local LLM model.  

Requires a valid API key for PicoVoice (https://picovoice.ai/)

## Local Installation

```
pip install -r requirements.txt
```

Copy the sample.env file to .env, add in your picovoice API key, and change any of the prompts or wakewords.

## Running Bumblebee Voice App

Make sure your mic and speakers are working, as this app is entirely voice input/output!

```
./bb.sh

or 

bb.bat
```

**NOTE: TTS is only working with linux right now, I'm fixing it...**

## llama.cpp - Run the LLM Model locally

This app requires llama.cpp running in server mode on the same machine or another machine on your network.  The default prompt format will work well with any ChatML trained model like https://huggingface.co/NousResearch/Hermes-2-Pro-Llama-3-8B-GGUF

Follow the instructions on their github repo to get it working:

https://github.com/ggerganov/llama.cpp

## whisper.cpp - Run the Transcriber locally
 
This app requires whisper.cpp running in server mode on the same machine or another machine on your network.  It will work fine with the base_en model.  Follow the instructions on their gitub repo to get it running:

https://github.com/ggerganov/whisper.cpp

