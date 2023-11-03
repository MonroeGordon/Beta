import azure.cognitiveservices.speech as speechsdk
import keyboard
import openai
import os
import pyaudio
import speech_recognition as sr
import time
import wave

# Load environment and obtain API keys
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv())

azure_api_key = os.environ.get('SPEECH_KEY')
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Beta class creates and runs the Beta chatbot that is capable of speech recognition, speech output, and language
# comprehension via OpenAI's GPT-3.5.
class Beta:
    # Initialize the Beta chatbot
    def __init__(self):
        # Define the maximum number of words GPT can handle
        self.MAX_WORDS = 3000
        
        # Initialize microphone and speech recognizer
        self.microphone = sr.Microphone()
        self.recognizer = sr.Recognizer()
        
        # Initialize stop variable for stopping Beta's run loop
        self.stop = False
        
        # Initialize pause variable for pausing Beta's speech response
        self.paused = False
        
        # Initialize variables for flagging when a user wants to speak or text
        self.user_speaking = False
        self.user_texting = False
        
        # Initialize a list to store all the messages to and from Beta
        self.message_history = []
        
        # Create responses directory if it doesn't exist
        try:
            os.mkdir("responses")
        # Clear the old response files if any exists
        except FileExistsError:
            dir_list = os.listdir("responses")
            
            for file in dir_list:
                os.remove("responses/" + file)
        
        # Initialize variables for speech recognition and synthesis
        self.speech_filename = "responses/speech"
        self.responses = 0
        self.wav_file = None
        
        self.speech_config = speechsdk.SpeechConfig(
            subscription=azure_api_key,
            region="westus")

        listen_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        
        self.speech_config.speech_recognition_language="en-US"
        self.speech_config.speech_synthesis_voice_name='en-US-EricNeural'
        
        self.speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config, 
            audio_config=listen_config)
       
        # Run Beta
        self.run()
        
    # Read and return data from the wave file
    # in_data - unused
    # frame_count - number of frames in the audio
    # time_info - unused
    # status - unused
    # returns - audio data from the wave file
    def audio_callback(self, in_data, frame_count, time_info, status):
        data = self.wav_file.readframes(frame_count)
        return (data, pyaudio.paContinue)
        
    # Helper function for completing chat responses.
    # prompt - the prompt to give GPT
    # model - the GPT model to use
    # temperature - the degree of randomness in GPT's responses
    # returns - the content of the response message from GPT
    def get_completion(self, prompt, model="gpt-3.5-turbo", 
                       temperature=0.3, role="user", remember_response=True) -> str:
        # Add the new prompt to the message history and then produce a response to
        # the prompt
        self.message_history.append({"role": role, "content": prompt})
        response = openai.ChatCompletion.create(
            model=model,
            messages=self.message_history,
            temperature=temperature
        )
        
        # If remembering the response, add the response to the message history
        if(remember_response is True):
            self.message_history.append({"role": "assistant", "content": 
                                         response.choices[0].message["content"]})
                
        # If word count exceeds max word length for GPT
        if self.get_word_count() >= self.MAX_WORDS:
            # Remove the third and fourth messages (first user prompt and its response) 
            # in the message history .
            # (the first and second messages are permanent system messages to GPT)
            self.message_history.pop(3)
            self.message_history.pop(2)
        
        # Return the response
        return response.choices[0].message["content"]
    
    # Returns the number of words that have been exchanged in the chat history
    # returns - the number of words exchanged in the chat history
    def get_word_count(self):
        count = 0
        
        for m in self.message_history:
            count += len(m["content"].split())
            
        return count
    
    # Initialize GPT (performed at the start and every time the max token length has
    # been reached)
    def initialize_gpt(self):
        # Give GPT a system prompt to initialize it and set its behavior.
        self.get_completion(("Your personal name is Beta. Do not call yourself OpenAI"
                             " Assistant. Do not call yourself an AI language model." 
                             " Compute math equations step by step and check your"
                             " solution."
                             "When a user asks for help, give the following statements:\n"
                             "1. Press the 'spacebar' to speak your message.\n"
                             "2. Press the 't' key to type your message.\n"
                             "3. You may stop me mid-speech by pressing 'spacebar' or 't'."
                             "4. You may also press 'p' to pause my speech."
                             "5. To leave our conversation, you can press 'x'."),
                            role="system", remember_response=False)
        

    # Continually listen for speech from the user via microphone.
    # returns - text form of the speech Beta heard
    def listen(self):
        print("Listening...")
        
        speech_recognition_result = self.speech_recognizer.recognize_once_async().get()

        if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
            result = speech_recognition_result.text
            print("Beta Heard: {}".format(speech_recognition_result.text))
            return result
        elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
            print("Beta Heard: {no speech}")
            return ""
        elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_recognition_result.cancellation_details
            print("Speech Recognition canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print("Error details: {}".format(cancellation_details.error_details))
                print("Did you set the speech resource key and region values?")
            return ""
    
    # Run Beta's processing loop
    def run(self):
        # Inform user of Beta's initialization
        print("\nInitializing Beta...\n")
        
        # Initialize GPT
        self.initialize_gpt()
        
        # Have Beta display greeting and help information
        response = self.get_completion(("State your name and display help "
                                        "information"),
                                       role="system", remember_response=True)
        
        # Display and speak responses
        print("Beta: " + response)
        self.speak(response)
        
        # Run until stopped 
        while(not self.stop): 
            try:
                user_input = ""
                response = []
                typed = False
                
                # When the spacebar is pressed or has been pressed
                if keyboard.is_pressed(" ") or self.user_speaking is True:
                    # Listen to the user
                    user_input = self.listen()
                    self.user_speaking = False
                # When t is pressed or has been pressed
                elif keyboard.is_pressed("t") or self.user_texting is True:
                    # Receive text input from the user
                    print("Your Input: ")
                    user_input = str(input())
                    print("Beta Read: {}".format(user_input))
                    typed = True
                    self.user_texting = False
                # When x is pressed, say goodbye
                elif keyboard.is_pressed('x'):
                    self.say_goobye()
                    
                # If input was received from the user
                if(user_input != ""):
                    # Retrieve response to user's prompt
                    response = self.get_completion(prompt=user_input)
                    
                    # Display and speak responses
                    print("Beta: " + response)
                        
                    # If user spoke, have Beta speak
                    if(typed is False):
                        self.speak(response)
            # Stop when keyboard interrupt occurs
            except KeyboardInterrupt: 
                self.stop = True
                
        # Remove speech response files
        dir_list = os.listdir("responses")
        
        for file in dir_list:
            os.remove("responses/" + file)
                
    # Have Beta day goodbye and stop Beta's run loop
    def say_goobye(self):
        print("\nEnding conversation...\n")
        response = self.get_completion("Say goodbye to the user.", role="system",
                                       remember_response=True)
        print("Beta: " + response)
        self.speak(response)
        self.stop = True
        
    # Speak the specified text
    # text - string to speak
    def speak(self, text: str):
        # Synthesize speech from the text
        self.responses += 1
        
        speak_config = speechsdk.audio.AudioOutputConfig(
            filename=self.speech_filename + str(self.responses) + ".wav")

        speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config, 
            audio_config=speak_config)
        
        result = speech_synthesizer.speak_text_async(text).get()
        
        # Handle speech cancellation and/or error
        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print("Speech synthesis canceled: {}".format(cancellation_details.reason))
            
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print("Error details: {}".format(cancellation_details.error_details))
                
            # Exit function on cancellation or error
            return
        
        # Open a new wave file for the speech synthesis
        self.wav_file = wave.open(self.speech_filename + str(self.responses) + ".wav", 
                                  'rb')
        pa = pyaudio.PyAudio()
        
        # Read the audio stream from the wave file
        stream = pa.open(format=pa.get_format_from_width(self.wav_file.getsampwidth()),
                         channels=self.wav_file.getnchannels(),
                         rate=self.wav_file.getframerate(),
                         output=True,
                         stream_callback=self.audio_callback)

        # Play the audio stream
        stream.start_stream()     
        
        # While audio plays, check for pausing or stopping
        while stream.is_active() or self.paused is True:
            # Pause/unpause Beta's speech
            if keyboard.is_pressed("p"):
                if self.paused is False:
                    stream.stop_stream()
                    self.paused = True
                else:
                    stream.start_stream()
                    self.paused = False
            # Stop Beta's speech and prepare to listen to the user
            elif keyboard.is_pressed(" "):
                if self.paused is False:
                    stream.stop_stream()
                else:
                    self.paused = False
                    
                self.user_speaking = True
            # Stop Beta's speech and prepare for user's text input
            elif keyboard.is_pressed("t"):
                if self.paused is False:
                    stream.stop_stream()
                else:
                    self.paused = False
                    
                self.user_texting = True
            # Stop Beta's current speech and say goodbye
            elif keyboard.is_pressed('x'):
                if self.paused is False:
                    stream.stop_stream()
                else:
                    self.paused = False
                    
                self.say_goobye()
                
            time.sleep(0.1)
           
        # Stop and close stream and close and delete the wave file
        stream.stop_stream()
        stream.close()
        self.wav_file.close()
        pa.terminate()

# Main function
def main():
    Beta()


if __name__ == '__main__':
    main() 
