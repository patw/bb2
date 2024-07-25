#!/bin/sh
echo $@ | piper --model glados.onnx --output-raw | aplay -r 22050 -f S16_LE -t raw -
