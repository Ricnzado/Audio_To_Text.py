import os
import time
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence
import noisereduce as nr  # Noise reduction library

# FFmpeg Pfad zur Umgebungsvariable PATH hinzufügen
ffmpeg_path = r"C:\Users\ricar\ffmpeg-2024-09-16-git-76ff97cef5-full_build\ffmpeg-2024-09-16-git-76ff97cef5-full_build\bin"
os.environ["PATH"] += os.pathsep + ffmpeg_path

# Pfad zur WAV-Datei
wav_file_path = r"C:\Users\ricar\OneDrive\Desktop\01_Datei.wav"

# Output-Verzeichnis für die Chunks
output_dir = "output_chunks"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Prüfen, ob die Datei existiert
if os.path.exists(wav_file_path):
    print("Datei gefunden, starte Verarbeitung...")

    # Lade die WAV-Datei mit pydub (ohne Änderung der Abtastrate)
    audio = AudioSegment.from_wav(wav_file_path)

    # Prüfen, ob die Datei erfolgreich geladen wurde
    if len(audio) > 0:
        print(f"Datei wurde erfolgreich geladen: {wav_file_path}")
        
        # Teile die Datei basierend auf Pausen
        chunks = split_on_silence(
            audio,
            min_silence_len=500,  # Dauer der Pause in Millisekunden
            silence_thresh=-30  # Lautstärkepegel für "Stille" (Anpassen, wenn nötig)
        )

        # Erstelle ein Recognizer-Objekt
        r = sr.Recognizer()

        # Liste für die Transkriptionen
        transcripts = []
        max_retries = 5  # Anzahl der Wiederholungsversuche

        for idx, chunk in enumerate(chunks):
            # Speichere jeden Abschnitt als eigene Datei
            chunk_filename = os.path.join(output_dir, f"chunk_{idx}.wav")
            chunk.export(chunk_filename, format="wav")
            print(f"Verarbeite Abschnitt {idx + 1}/{len(chunks)}: {chunk_filename}")

            # Optional: Rauschunterdrückung auf den Chunk anwenden
            try:
                # Lade das Chunk und wende Rauschunterdrückung an
                raw_audio = AudioSegment.from_wav(chunk_filename)
                reduced_noise = nr.reduce_noise(y=raw_audio.get_array_of_samples(), sr=raw_audio.frame_rate)
                
                # Erstelle eine neue Audiodatei mit der reduzierten Geräuschkulisse
                noise_reduced_chunk_filename = os.path.join(output_dir, f"denoised_chunk_{idx}.wav")
                reduced_noise_segment = AudioSegment(
                    reduced_noise.tobytes(), 
                    frame_rate=raw_audio.frame_rate,
                    sample_width=raw_audio.sample_width, 
                    channels=raw_audio.channels
                )
                reduced_noise_segment.export(noise_reduced_chunk_filename, format="wav")

            except Exception as e:
                print(f"Rauschunterdrückung fehlgeschlagen für Abschnitt {idx + 1}: {e}")
                noise_reduced_chunk_filename = chunk_filename  # Verwende Originaldatei, wenn Fehler auftritt

            retries = 0
            success = False

            while retries < max_retries and not success:
                try:
                    # Öffnen des Abschnitts zur Transkription
                    with sr.AudioFile(noise_reduced_chunk_filename) as source:
                        audio_data = r.record(source)  # Lesen des gesamten Abschnitts
                        
                        # Transkription mit Google Web Speech API (Deutsch)
                        text = r.recognize_google(audio_data, language="de-DE")
                        print(f"Transkription erfolgreich für Abschnitt {idx + 1}: ", text)

                        # Füge die Transkription der Liste hinzu
                        transcripts.append(text)
                        success = True  # Wenn es erfolgreich ist, verlässt die Schleife
                    
                    # Warte 2 Sekunden, um die Rate der Anfragen zu verlangsamen
                    time.sleep(2)
                
                except sr.UnknownValueError:
                    print(f"Abschnitt {idx + 1} konnte nicht verstanden werden. Versuch {retries + 1}/{max_retries}.")
                
                except sr.RequestError as e:
                    print(f"Fehler bei der Anfrage an die Spracherkennungs-API für Abschnitt {idx + 1}: {e}. Versuch {retries + 1}/{max_retries}.")
                
                except Exception as e:
                    print(f"Ein unerwarteter Fehler trat bei Abschnitt {idx + 1} auf: {e}. Versuch {retries + 1}/{max_retries}.")
                
                retries += 1

            if not success:
                print(f"Abschnitt {idx + 1} konnte nach {max_retries} Versuchen nicht transkribiert werden.")

        # Transkriptionen zusammenführen und in einer Datei speichern
        final_transcript_path = os.path.join(output_dir, "final_transcript.txt")
        with open(final_transcript_path, "w", encoding="utf-8") as final_file:
            for transcript in transcripts:
                final_file.write(transcript + "\n")
        print(f"Alle Transkriptionen wurden erfolgreich zusammengeführt und in {final_transcript_path} gespeichert.")
        
    else:
        print(f"Datei konnte nicht geladen werden. Bitte überprüfen Sie den Pfad.")
else:
    print(f"Datei nicht gefunden: {wav_file_path}. Bitte überprüfen Sie den Pfad.")
